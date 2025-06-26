import os
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv
import pandas as pd 
import seaborn as sns 
import json
from datetime import datetime


data = "scrims.json"

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
    def __init__(self, adversario, mapa):
        super().__init__()
        self.adversario = adversario
        self.mapa = mapa

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
            "usuario_id": str(interaction.user.id)
        }
        dados.append(nova_scrim)
        datasave(dados)
        await interaction.response.send_message(f"✅ Scrim registrada como **{resultado.upper()}** contra `{self.adversario}` no mapa `{self.mapa}`", ephemeral=True)


class DataWrapper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="scrim")
    async def scrim_comando(self, ctx, adversario: str, *, mapa: str = "Summoner's Rift"):
        embed = discord.Embed(title="Registrar Scrim", color=discord.Color.blurple())
        embed.add_field(name="Adversário", value=adversario)
        embed.add_field(name="Mapa", value=mapa)
        embed.set_footer(text="Clique em Vitória ou Derrota para registrar")

        await ctx.send(embed=embed, view=ScrimButtons(adversario, mapa))

    @commands.command(name="listar_scrims")
    async def listar_scrims(self, ctx):
        dados = dataload()
        if not dados:
            await ctx.send("📭 Nenhuma scrim registrada ainda.")
            return

        texto = ""
        for s in dados[-10:]:  # últimos 10
            resultado = "✅" if s["resultado"] == "vitória" else "❌"
            texto += f"{resultado} {s['adversario']} ({s['mapa']}) por <@{s['usuario_id']}> em {s['data'][:10]}\n"

        await ctx.send(f"📋 Últimas scrims registradas:\n```{texto}```")


async def setup(bot):
    await bot.add_cog(DataWrapper(bot))