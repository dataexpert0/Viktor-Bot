import discord
from discord.ext import commands
from discord import app_commands
import openmeteo_requests
import requests_cache
from retry_requests import retry

# Classe para o menu de seleção de cidades
class CidadeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="São Paulo", 
                description="Ver clima de São Paulo", 
                emoji="🌆",
                value="sao_paulo"
            ),
            discord.SelectOption(
                label="Rio de Janeiro", 
                description="Ver clima do Rio de Janeiro", 
                emoji="🏖️",
                value="rio_janeiro"
            ),
            discord.SelectOption(
                label="Ambas as cidades", 
                description="Ver clima de São Paulo e Rio de Janeiro", 
                emoji="🌍",
                value="ambas"
            )
        ]
        super().__init__(placeholder="Escolha uma cidade...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Determinar quais cidades mostrar
        if self.values[0] == "ambas":
            cidades_selecionadas = ["sao_paulo", "rio_janeiro"]
        else:
            cidades_selecionadas = [self.values[0]]
        
        # Buscar dados do clima através da cog Utils
        utils_cog = interaction.client.get_cog("Utils")
        if utils_cog:
            embeds = await utils_cog.get_weather_data(cidades_selecionadas)
            await interaction.followup.send(embeds=embeds)
        else:
            await interaction.followup.send("Erro ao acessar dados do clima.", ephemeral=True)

class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Comando de Slash (/clima) dinâmico com menu de seleção
    @app_commands.command(name="clima", description="Consulta o clima atual com menu de seleção de cidades")
    async def clima(self, interaction: discord.Interaction):
        # Criar o menu dropdown
        select = CidadeSelect()
        view = discord.ui.View()
        view.add_item(select)
        
        embed = discord.Embed(
            title="🌤️ Consulta de Clima",
            description="Escolha uma cidade para ver o clima atual:",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Selecione uma opção no menu abaixo")
        
        await interaction.response.send_message(embed=embed, view=view)

    # Função auxiliar para buscar dados do clima
    async def get_weather_data(self, lugares_selecionados):
        # Setup de cache e retries para a API (requests)
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        url = "https://api.open-meteo.com/v1/forecast"

        # Dicionário com todas as cidades disponíveis
        todas_cidades = {
            "sao_paulo": {"cidade": "São Paulo", "lat": -23.5505, "lon": -46.6333},
            "rio_janeiro": {"cidade": "Rio de Janeiro", "lat": -22.9035, "lon": -43.2096}
        }
        
        # Lista para guardar os embeds que serão enviados
        embeds_to_send = []
        
        # Iteração que prepara os embeds para cada cidade selecionada
        for cidade_key in lugares_selecionados:
            lugar = todas_cidades[cidade_key]
            
            params = {
                "latitude": lugar["lat"],
                "longitude": lugar["lon"],
                "daily": ["temperature_2m_max", "temperature_2m_min"],
                "current": ["temperature_2m", "is_day", "precipitation"],
                "timezone": "America/Sao_Paulo"
            }

            responses = openmeteo.weather_api(url, params=params)
            response = responses[0]

            # Processamento dos dados da API
            current = response.Current()
            temperatura = current.Variables(0).Value()
            is_day_value = current.Variables(1).Value()
            chuva = current.Variables(2).Value()

            is_day_text = "🌞 Dia" if is_day_value == 1.0 else "🌙 Noite"
            
            # Criação do Embed/UI para interação com o usuário
            embed = discord.Embed(
                title=f"Clima em {lugar['cidade']}",
                description=is_day_text,
                color=discord.Color.blue()
            )
            embed.add_field(name="🌡️ Temperatura atual", value=f"{temperatura:.1f}°C", inline=True)
            embed.add_field(name="☔ Precipitação", value=f"{chuva:.1f} mm", inline=True)
            embed.set_footer(text="Fonte: Open-Meteo API")
            
            embeds_to_send.append(embed)

        return embeds_to_send

    @app_commands.command(name="help", description="Consulta as informações básicas do bot.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embedhelp = discord.Embed(
            title = f"Bem-vindo a gloriosa evolução!",
            description = f"O Viktor Bot é um auxiliar para várias necessidades em utilidades básicas, tratamento de dados, entre outros.",
            color = discord.Color.blue()
        )
        embedhelp.add_field(name = "Autoria", value = "Atualmente sendo desenvolvido por dataexpert0.", inline=True)
        embedhelp.add_field(name = "Linguagem utilizada", value = "Python", inline = True)
        embedhelp.add_field(name = "Tecnologias", value = "Plotagem de gráficos, transformação de dados casuais, entre outros", inline=True)
        embedhelp.set_footer(text = "Documentação: https://github.com/dataexpert0/Viktor-Bot")
        
        await interaction.followup.send(embed = embedhelp)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))