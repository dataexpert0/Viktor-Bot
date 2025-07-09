import discord
from discord.ext import commands
from discord import app_commands
import openmeteo_requests
import requests_cache
from retry_requests import retry

class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Comando de Slash (/clima) dinâmico
    @app_commands.command(name="clima", description="Consulta o clima atual de São Paulo e Rio de Janeiro")
    async def clima(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Setup de cache e retries para a API (requests)
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        url = "https://api.open-meteo.com/v1/forecast"

        # Consulta somente às cidades de SP e RJ
        lugares = [
            {"cidade": "São Paulo", "lat": -23.5505, "lon": -46.6333},
            {"cidade": "Rio de Janeiro", "lat": -22.9035, "lon": -43.2096}
        ]
        
        # Lista para guardar os embeds que serão enviados
        embeds_to_send = []
        
        # Iteração que prepara os embeds para cada cidade
        for lugar in lugares:
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
                color=discord.Color.blue()  # Usando uma cor azul padrão do Discord
            )
            embed.add_field(name="🌡️ Temperatura atual", value=f"{temperatura:.1f}°C", inline=True)
            embed.add_field(name="☔ Precipitação", value=f"{chuva:.1f} mm", inline=True)
            embed.set_footer(text="Fonte: Open-Meteo API")
            
            embeds_to_send.append(embed)

        await interaction.followup.send(embeds=embeds_to_send)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))