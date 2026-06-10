import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
import json
import tempfile
import openmeteo_requests
import requests_cache
from bs4 import BeautifulSoup
from retry_requests import retry
from datetime import datetime, timezone
from samp_client.client import SampClient

def envio_telegraph(image_path, mime_type='image/jpeg'):
    try:
        print(f"[TELEGRAPH] Iniciando upload do arquivo: {image_path}")
        print(f"[TELEGRAPH] MIME type: {mime_type}")
        
        # Verificar se o arquivo existe
        if not os.path.exists(image_path):
            print(f"[TELEGRAPH] Erro: Arquivo não encontrado: {image_path}")
            return None
            
        # Verificar o tamanho do arquivo
        file_size = os.path.getsize(image_path)
        print(f"[TELEGRAPH] Tamanho do arquivo: {file_size} bytes")
        
        # Verificar se o arquivo não está vazio
        if file_size == 0:
            print("[TELEGRAPH] Erro: Arquivo está vazio")
            return None
        
        # Verificar se o arquivo não é muito grande (Telegraph tem limite de ~5MB)
        if file_size > 5 * 1024 * 1024:
            print(f"[TELEGRAPH] Erro: Arquivo muito grande ({file_size} bytes). Limite: 5MB")
            return None
        
        # Primeiro tentar Telegraph
        telegraph_result = try_telegraph_upload(image_path, mime_type)
        if telegraph_result:
            return telegraph_result
            
        # Se Telegraph falhar, tentar serviços alternativos como fallback
        print("[UPLOAD] Telegraph falhou, tentando serviços alternativos como fallback...")
        return try_imgbb_upload(image_path)
        
    except Exception as e:
        print(f"[UPLOAD] Erro inesperado: {type(e).__name__}: {e}")
        import traceback
        print(f"[UPLOAD] Traceback: {traceback.format_exc()}")
        return None

def try_telegraph_upload(image_path, mime_type):
    try:
        with open(image_path, "rb") as f:
            print("[TELEGRAPH] Enviando requisição POST para telegra.ph...")
            
            # Tentar múltiplas abordagens
            attempts = [
                # Tentativa 1: Formato mais simples
                {'file': ('image.jpg', f, 'image/jpeg')},
                # Tentativa 2: Sem MIME type
                {'file': ('image.jpg', f)},
                # Tentativa 3: Só o arquivo
                {'file': f},
            ]
            
            for attempt_num, files_data in enumerate(attempts, 1):
                try:
                    print(f"[TELEGRAPH] Tentativa {attempt_num}")
                    
                    f.seek(0)
                    
                    response = requests.post(
                        'https://telegra.ph/upload',
                        files=files_data,
                        timeout=30,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                    )
                    
                    print(f"[TELEGRAPH] Tentativa {attempt_num} - Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"[TELEGRAPH] Dados recebidos: {data}")
                        
                        if isinstance(data, list) and len(data) > 0 and "src" in data[0]:
                            link = "https://telegra.ph" + data[0]["src"]
                            print(f"[TELEGRAPH] Sucesso na tentativa {attempt_num}! Link: {link}")
                            return link
                    else:
                        print(f"[TELEGRAPH] Tentativa {attempt_num} falhou: {response.text}")
                        
                except Exception as e:
                    print(f"[TELEGRAPH] Erro na tentativa {attempt_num}: {e}")
                    
        print("[TELEGRAPH] Todas as tentativas falharam")
        return None
        
    except Exception as e:
        print(f"[TELEGRAPH] Erro geral: {e}")
        return None

def try_imgbb_upload(image_path):
    try:
        print("[FALLBACK] Tentando upload para 0x0.st...")
        
        with open(image_path, "rb") as f:
            response = requests.post(
                'https://0x0.st',
                files={'file': f},
                timeout=30,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            
        print(f"[FALLBACK] Status: {response.status_code}")
        
        if response.status_code == 200:
            link = response.text.strip()
            print(f"[FALLBACK] Sucesso! Link: {link}")
            return link
        else:
            print(f"[FALLBACK] 0x0.st falhou: {response.text}")
            
            # Tentar outro serviço como segundo fallback
            return try_catbox_upload(image_path)
            
    except Exception as e:
        print(f"[FALLBACK] Erro no 0x0.st: {e}")
        # Tentar outro serviço como segundo fallback
        return try_catbox_upload(image_path)

def try_catbox_upload(image_path):
    try:
        print("[FALLBACK2] Tentando upload para catbox.moe...")
        
        with open(image_path, "rb") as f:
            response = requests.post(
                'https://catbox.moe/user/api.php',
                data={'reqtype': 'fileupload'},
                files={'fileToUpload': f},
                timeout=30,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            
        print(f"[FALLBACK2] Status: {response.status_code}")
        
        if response.status_code == 200:
            link = response.text.strip()
            if link.startswith('https://'):
                print(f"[FALLBACK2] Sucesso! Link: {link}")
                return link
            else:
                print(f"[FALLBACK2] Resposta inválida: {link}")
                return None
        else:
            print(f"[FALLBACK2] Catbox falhou: {response.text}")
            return None
            
    except Exception as e:
        print(f"[FALLBACK2] Erro no catbox: {e}")
        return None


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

    # Serviço de hospedagem de imagens via Viktor Bot - Telegraph | Catbox | 0x0.st
    @commands.command(name="hospedar")
    async def hospedar(self, ctx):
        await ctx.send(f"{ctx.author}, será feita a hospedagem da imagem através do serviço (Telegraph) - rota mais rápida. O link será enviado em seguida.")
        await ctx.send(f"Caso todas as rotas não sejam possíveis, o catbox.moe será utilizado como prioridade.")

        try:
            print(f"[HOSPEDAR] Comando iniciado pelo usuário: {ctx.author} ({ctx.author.id})")
            
            if not ctx.message.attachments:
                print("[HOSPEDAR] Erro: Nenhum anexo encontrado")
                await ctx.send("Envie o comando junto de uma imagem como anexo.")
                return
            
            imagem = ctx.message.attachments[0]
            print(f"[HOSPEDAR] Anexo detectado: {imagem.filename} ({imagem.size} bytes)")
            
            if not imagem.content_type or not imagem.content_type.startswith("image/"):
                print(f"[HOSPEDAR] Erro: Tipo de arquivo inválido: {imagem.content_type}")
                await ctx.send("O arquivo enviado não é uma imagem válida.")
                return

            print(f"[HOSPEDAR] Tipo de imagem válido: {imagem.content_type}")

            # Determinar extensão baseada no content_type se filename não tiver
            if imagem.filename:
                ext = os.path.splitext(imagem.filename)[1].lower()
            else:
                # Mapear content_type para extensão
                ext_mapping = {
                    'image/jpeg': '.jpg',
                    'image/jpg': '.jpg', 
                    'image/png': '.png',
                    'image/gif': '.gif',
                    'image/webp': '.webp'
                }
                ext = ext_mapping.get(imagem.content_type.lower(), '.jpg')
            
            # Se não houver extensão, usar .jpg como padrão
            if not ext:
                ext = '.jpg'
                
            print(f"[HOSPEDAR] Extensão determinada: {ext}")
            mime = imagem.content_type
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                print(f"[HOSPEDAR] Salvando imagem temporariamente: {tmp.name}")
                tmp_path = tmp.name
            
            # Salvar o arquivo fora do context manager
            await imagem.save(tmp_path)
            
            # Verificar se o arquivo foi salvo corretamente
            if not os.path.exists(tmp_path):
                print(f"[HOSPEDAR] Erro: Arquivo não foi salvo corretamente: {tmp_path}")
                await ctx.send("Erro ao salvar a imagem temporariamente.")
                return
                
            saved_size = os.path.getsize(tmp_path)
            print(f"[HOSPEDAR] Arquivo salvo com sucesso. Tamanho: {saved_size} bytes")
            
            try:
                print("[HOSPEDAR] Enviando imagem para Telegraph...")
                link = envio_telegraph(tmp_path, mime)
                if link:
                    print(f"[HOSPEDAR] Sucesso! Link gerado: {link}")
                    await ctx.send(f"Imagem hospedada: {link}")
                else:
                    print("[HOSPEDAR] Erro: Telegraph retornou None")
                    await ctx.send("Falha ao enviar a imagem para o serviço de hospedagem (Telegraph).")
            except Exception as e:
                print(f"[HOSPEDAR] Erro durante envio para Telegraph: {type(e).__name__}: {e}")
                await ctx.send("Erro interno ao processar a imagem. Tente novamente.")
            finally:
                try:
                    os.remove(tmp_path)
                    print(f"[HOSPEDAR] Arquivo temporário removido: {tmp_path}")
                except Exception as e:
                    print(f"[HOSPEDAR] Aviso: Falha ao remover arquivo temporário: {e}")
                    
        except Exception as e:
            print(f"[HOSPEDAR] Erro crítico no comando: {type(e).__name__}: {e}")
            import traceback
            print(f"[HOSPEDAR] Traceback completo:\n{traceback.format_exc()}")
            await ctx.send("Ocorreu um erro inesperado. Verifique os logs do terminal.")

    @commands.command(name = "sampinfo")
    async def sampinfo(self, ctx):
        try:
            response = requests.get("https://api.open.mp/servers/80.75.221.41:7777")

            if response.status_code != 200:
                print("A requisição falhou!")
                return

            data = response.json()

            server = data['core']

            hostname = server.get('hn', 'Servidor sem nome')
            players = server.get('pc', "Desconhecido | Sem jogadores")
            lastupdate = data['lastUpdated']
            lastupdate_dt = datetime.strptime(lastupdate, "%Y-%m-%dT%H:%M:%S.%fZ")
            lastupdate_dt = lastupdate_dt.replace(tzinfo=timezone.utc)

            embed = discord.Embed(
                title = hostname,
                description = f"Jogadores: {info.players}\nÚltima atualização em formato UTC: {lastupdate_dt}",
                color = 0x00ff00
            )
            embed.set_footer(text="Dados retirados via | Open.mp")
            await ctx.send(embed = embed)

        except Exception as e:
            await ctx.send("Houve um erro ao realizar o famoso web-scraping no site Open-MP. Tente novamente mais tarde.")
            print(e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))