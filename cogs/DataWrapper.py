import os
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord import app_commands
from dotenv import load_dotenv
import pandas as pd 
import seaborn as sns 
import json
import matplotlib.pyplot as plt
from datetime import datetime
import traceback
import requests
from bs4 import BeautifulSoup

load_dotenv()
riot_api_key = os.getenv('riot_api_key')

REGIONAL = "americas"
PLATFORM = "br1"

HEADERS = {
    "X-Riot-Token": riot_api_key
}

class ScrimModal(Modal, title = "Registrar Partida | Scrim"):
    def __init__(self):
        super().__init__(title="Registrar Partida | Scrim")

        self.comp_time_principal = TextInput(label="Composição da sua line", required=True)
        self.comp_adversario = TextInput(label="Composição adversária", required=True)
        self.adversario = TextInput(label="Nome do time adversário", required=True)
        self.line = TextInput(label="Line que jogou", required=True)
        self.resultado = TextInput(label="Vitória ou Derrota", required=True)

        self.add_item(self.comp_time_principal)
        self.add_item(self.comp_adversario)
        self.add_item(self.adversario)
        self.add_item(self.line)
        self.add_item(self.resultado)
        
    async def on_submit(self, interaction: discord.Interaction):
        dados = {
            "id": gerar_novo_id(dataload()),
            "data": str(datetime.now()),
            "resultado": self.resultado.value.lower(),
            "adversario": self.adversario.value,
            "mapa": "Summoner's Rift",
            "line": self.line.value,
            "usuario_id": str(interaction.user.id),
            "comp_tp": self.comp_time_principal.value,
            "comp_adv": self.comp_adversario.value,
        }

        if not os.path.exists("scrims.json"):
            with open("scrims.json", "w") as f:
                json.dump([], f)

        with open("scrims.json", "r") as f:
            historico = json.load(f)

        historico.append(dados)

        with open("scrims.json", "w") as f:
            json.dump(historico, f, indent=2)

        await interaction.response.send_message("Scrim registrada com sucesso!", ephemeral=True)


data = "scrims.json"

def riot_get_puuid(game_name: str, tag_line: str) -> str:
    url = (
        f"https://{REGIONAL}.api.riotgames.com/riot/account/v1/"
        f"accounts/by-riot-id/{game_name}/{tag_line}"
    )

    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    return response.json()["puuid"]


def riot_get_match_ids(puuid: str, count: int = 20, queue: int = 420) -> list[str]:
    url = (
        f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/"
        f"matches/by-puuid/{puuid}/ids"
    )

    params = {
        "start": 0,
        "count": count,
        "queue": queue
    }

    response = requests.get(url, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()

    return response.json()


def riot_get_match_detail(match_id: str) -> dict:
    url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/{match_id}"

    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    return response.json()


def extract_player_data_from_match(match: dict, puuid: str) -> dict | None:
    participants = match["info"]["participants"]

    player = next(
        (participant for participant in participants if participant["puuid"] == puuid),
        None
    )

    if player is None:
        return None

    return {
        "champion": player["championName"],
        "win": player["win"],
        "kills": player["kills"],
        "deaths": player["deaths"],
        "assists": player["assists"],
        "team_position": player.get("teamPosition", "UNKNOWN"),
        "queue_id": match["info"]["queueId"]
    }


def build_champion_summary(game_name: str, tag_line: str, count: int = 20, queue: int = 420) -> pd.DataFrame:
    puuid = riot_get_puuid(game_name, tag_line)
    match_ids = riot_get_match_ids(puuid, count=count, queue=queue)

    rows = []

    for match_id in match_ids:
        match = riot_get_match_detail(match_id)
        row = extract_player_data_from_match(match, puuid)

        if row is not None:
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    summary = (
        df.groupby("champion")
        .agg(
            games=("champion", "count"),
            wins=("win", "sum"),
            avg_kills=("kills", "mean"),
            avg_deaths=("deaths", "mean"),
            avg_assists=("assists", "mean")
        )
        .reset_index()
    )

    summary["losses"] = summary["games"] - summary["wins"]
    summary["win_rate"] = summary["wins"] / summary["games"] * 100
    summary["pick_frequency"] = summary["games"] / summary["games"].sum() * 100

    summary = summary.sort_values(["games", "win_rate"], ascending=False)

    return summary

def create_champion_heatmap(summary: pd.DataFrame, game_name: str, tag_line: str) -> str:
    heatmap_data = summary.set_index("champion")[
        ["win_rate", "pick_frequency"]
    ].round(1)

    height = max(5, len(heatmap_data) * 0.55)

    plt.figure(figsize=(9, height))

    sns.heatmap(
        heatmap_data,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        linewidths=0.5,
        linecolor="white",
        cbar=True
    )

    plt.title(f"Heatmap de Campeões - {game_name}#{tag_line}")
    plt.xlabel("Métricas")
    plt.ylabel("Campeão")
    plt.tight_layout()

    safe_name = f"{game_name}_{tag_line}".replace(" ", "_").replace("#", "_")
    image_path = f"heatmap_{safe_name}.png"

    plt.savefig(image_path, dpi=160, bbox_inches="tight")
    plt.close()

    return image_path

def dataload():
    if not os.path.exists(data):
        with open(data, "w") as f:
            json.dump([], f)
    with open(data, "r") as f:
        return json.load(f)
    
def datasave(dados):
    with open(data, "w") as f:
        json.dump(dados, f, indent=2)

def gerar_novo_id(dados):
    return max([s['id'] for s in dados], default=0) + 1

class ScrimButtons(View):
    def __init__(self, line, adversario, mapa):
        super().__init__()
        self.adversario = adversario
        self.mapa = mapa
        self.line = line

    @discord.ui.button(label="Vitória", style=discord.ButtonStyle.success)
    async def vitoria_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.registrar_scrim(interaction, "vitória")

    @discord.ui.button(label="Derrota", style=discord.ButtonStyle.danger)
    async def derrota_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.registrar_scrim(interaction, "derrota")

    async def registrar_scrim(self, interaction, resultado):
        dados = dataload()
        nova_scrim = {
            "id": gerar_novo_id(dados),
            "data": datetime.now().isoformat(),
            "resultado": resultado,
            "adversario": self.adversario,
            "mapa": self.mapa,
            "line": self.line,
            "usuario_id": str(interaction.user.id),
            "comp_tp": "",
            "comp_adv": "",
        }
        dados.append(nova_scrim)
        datasave(dados)
        await interaction.response.send_message(f"✅ Scrim registrada como **{resultado.upper()}** contra `{self.adversario}` no mapa `{self.mapa}`", ephemeral=True)


class DataWrapper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="scrim")
    async def scrim_comando(self, ctx, line: str, adversario: str, *, mapa: str = "Summoner's Rift"):
        embed = discord.Embed(title="Registrar Scrim", color=discord.Color.blurple())
        embed.add_field(name="Adversário", value=adversario)
        embed.add_field(name="Mapa", value=mapa)
        embed.add_field(name="Line", value=line)
        embed.set_footer(text="Clique em Vitória ou Derrota para registrar")

        await ctx.send(embed=embed, view=ScrimButtons(line, adversario, mapa))


    @commands.command(name = "heatmap")
    async def heatmap(self, ctx, game_name: str , tag_line: str, count: int = 10, queue: int = 420):

        await ctx.send("Buscando partidas através da Riot API, por favor, aguarde.")

        try:
            if count < 1: 
                await ctx.send("O número de partidas deve ser maior do que 0.")
                return
            
            if count > 50:
                await ctx.send("Use no máximo 50 partidas por requisição no momento.")
                return
            
            summary = await asyncio.to_thread(build_champion_summary, game_name, tag_line, count, queue)

            if summary.empty: 
                await ctx.send("O jogador em questão não possui partidas recentes ou não foi encontrado.")
                return
            
            image_path = await asyncio.to_thread(create_champion_heatmap, summary, game_name, tag_line)

            embed = discord.Embed(
                title = "📊 Heatmap de Campeões",
                description=(
                    f"Jogador: `{game_name}#{tag_line}`\n"
                    f"Partidas analisadas: `{count}`\n"
                    f"Queue: `{queue}/Ranked Solo/Duo`"
                ),
                color = discord.Color.green()
            )

            file = discord.File(image_path, filename="heatmap.png")
            embed.set_image(url="attachment://heatmap.png")

            await ctx.send(embed=embed, file=file)

            if os.path.exists(image_path):
                os.remove(image_path)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else "desconhecido"

            if status_code == 401:
                await ctx.send("Erro 401. No momento indisponível para uso.")
            elif status_code == 403: 
                await ctx.send("Erro 403. Endpoint inacessível no momento.")
            elif status_code == 404: 
                await ctx.send("Jogador não encontrado. Verifique o nome e tag.")
            elif status_code == 429: 
                await ctx.send("Limite de requisições atingido. Tente novamente mais tarde.")
            else:
                await ctx.send(f"Tente novamente mais tarde.")

        except Exception as e: 
            traceback.print_exc()
            await ctx.send(f"Ocorreu um erro inesperado: {e}")


    @commands.command(name="listar_scrims")
    async def listarscrims(self, ctx):
        dados = dataload()
        if not dados:
            await ctx.send("📭 Nenhuma scrim registrada ainda.")
            return

        texto = ""
        for s in dados[-10:]:
            resultado = "✅" if s["resultado"] == "vitória" else "❌"
            texto += f"{resultado} {s['adversario']} {s['line']} ({s['mapa']}) por <@{s['usuario_id']}> em {s['data'][:10]}\n"

        await ctx.send(f"📋 Últimas scrims registradas:\n```{texto}```")

    @commands.command(name = "resultstats")
    async def resultstats(self, ctx):
        dados = dataload()
        if not dados:
            await ctx.send("Não existe nenhuma scrim registrada ainda.")
            return
        
        df = pd.DataFrame(dados)

        vitorias = 0
        derrotas = 0

        for resultados in df['resultado']:
            if resultados == "vitória":
                vitorias += 1
            else:
                derrotas += 1

        plt.pie([vitorias, derrotas], labels = ["Vitórias", "Derrotas"], autopct = "%1.1f%%", colors = ["#66bb6a", "#ef5350"])
        plt.title("Taxa de Vitória nas Scrims")

        imagem_path = "resultados_scrims.png"
        plt.savefig(imagem_path)
        plt.close()

        await ctx.send(file=discord.File(imagem_path))

    @app_commands.command(name = "registrar", description = "Registrar scrim através de formulário")
    async def registrar(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(ScrimModal())
        except Exception as e:
            print(f"Debug: {e}")
            traceback.print_exc()

            
    @app_commands.command(name = "patchnotes", description = "Retorna um embed com as informações do patch notes atual")
    async def patchnotes(self, interaction: discord.Interaction):
        try:
            response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
            response.raise_for_status()
            versions = response.json()

            versao_recente = versions[0]
            patchver = f"2{versao_recente[1]}-{versao_recente.split('.')[1]}"

            patch_url = f"https://www.leagueoflegends.com/pt-br/news/game-updates/league-of-legends-patch-{patchver}-notes/"

            response = requests.get(patch_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            title_tag = soup.find("h1")
            summary_tag = soup.find("p")
            patch_image = soup.find("img")
            img_url = "https://cmsassets.rgpub.io/sanity/images/dsfx7636/news_live/078e912a89ff27a60699425065aecbc478435969-1920x1080.png"

            title = title_tag.get_text(strip=True) if title_tag else f"Patch {patchver}"
            summary = summary_tag.get_text(strip=True) if summary_tag else "Resumo não disponível."
            
            embed = discord.Embed(
                title = title,
                url = patch_url,
                description = summary,
                color = discord.Color.blue()
            )
            embed.set_image(url = img_url)
            embed.set_footer(text="Fonte: Riot Games • Data Dragon")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro ao buscar o patch notes: {e}")

async def setup(bot):
    await bot.add_cog(DataWrapper(bot))