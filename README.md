# Viktor Bot 

## Um assistente de análise de dados para Discord

![We lost ourselves. Lost our dream. In the pursuit of great, we failed to do good.](https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRcjHgKqznqAmj0LfhM5XbVmm66T2TtuJwvhR7byEZdLWfLUSKJIRSBLGgw5mRrMrOo9_g&usqp=CAU)

*We lost ourselves. Lost our dream. In the pursuit of great, we failed to do good.*

O **Viktor Bot** é um robô para Discord em linguagem Python (usando a discord.py) que foi criado inicialmente para cumprir as exigências de um servidor de Discord que comporta os membros de um time focado em League of Legends (LoL). O intuito em relação às funcionalidades dele são diversas, mas o foco é em análise exploratória de dados a partir de resultados dos jogos do time, utilizando ferramentas como scikit-learn, Seaborn, Pandas, ggplot2, Jupyter Notebooks, API(s) da própria Riot e outras fontes de dados. No momento, encontra-se sob fase de testes e de desenvolvimento.

## Features

Nessa aba, ficará algumas propostas de implementação.

• coleta de dados dos jogos automatizada através de API(s) 
• análise individual da performance de um time baseado em winrates, trends, composições, etc;
• insights com ferramentas de ML;
• visualização de dados através de charts ex.: *plots em Seaborn/ggplot2*

## Código

O *Viktor Bot* é primariamente escrito em Python 3.x, mas existe a possibilidade de ter outras propostas em Java, C++, entre outros.

## Utilização

O bot já possui alguns comandos básicos, como o registro de *scrims* através de Discord.UI, que é transferido para um arquivo .JSON criado na raíz. 

*!scrim [line da equipe] [adversário] [mapa ou modalidade escolhida, ao dispor do usuário]*
*!listarscrims* - retorna o resultado de todas as scrims registradas até o momento
*!resultstats* - retorna um gráfico de pizza em ggplot2 contendo as vitórias e derrotas da equipe/taxas de vitória e derrota
