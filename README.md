# ⚡ Auto Key Clicker (Multi-Monitor & Gaming Edition)

[![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](https://github.com/wellingtonpereira12/AutoKeyClicker/releases)
[![Download](https://img.shields.io/badge/Download-AutoKeyClicker.exe-success.svg)](https://autokeyclicker.pampo.tech/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(64--bit)-lightgrey.svg)]()
[![SSL](https://img.shields.io/badge/HTTPS-Secure%20Lock-green.svg)](https://autokeyclicker.pampo.tech/)

Um software profissional, leve e ultra-responsivo de repetição automática de teclas (**Auto-Clicker de Teclado**), desenvolvido especificamente para jogos e ambientes com **múltiplas telas (multitelas)**.

🌐 **Site Oficial & Download Seguro (HTTPS)**: [https://autokeyclicker.pampo.tech/](https://autokeyclicker.pampo.tech/)

---

## 🎯 Principais Funcionalidades

1. **Interface Compacta em Abas & Modo Mini / HUD (Novo!)**:
   - **Abas Organizadas**: Reduziu pela metade a altura da janela!
     - *Aba 1 (Teclas & Setups)*: Seleção do jogo, salvar/carregar perfis e quadradinhos das teclas.
     - *Aba 2 (Opções & Modo)*: Segundo plano vs foco, anti-ban e atalhos.
   - **Botão `🗗 Modo Mini`**: Esconde todas as configurações pesadas e transforma o programa em uma barra flutuante super discreta (HUD):
     - Mostra os **quadradinhos de todas as teclas configuradas** de forma puramente visual (não editável), exibindo o nome da tecla, o tempo e o **mesmo tubinho animado** enchendo e clicando em tempo real!
     - Mantém o status, contador de cliques/tempo e os botões de Iniciar/Parar.
   - Clique em `⚙️ Expandir` a qualquer momento para voltar à tela completa de edição e configurações.

2. **Seleção Inteligente de Janelas / Jogos Abertos**:
   - Uma lista suspensa (setinha) detecta **apenas executáveis e jogos reais abertos** (ex: `ragnarok.exe`, `RF_Online.bin`, etc.).
   - Filtra automaticamente processos de sistema em segundo plano do Windows, pastas e janelas invisíveis.
   - Atualização dinâmica (ao clicar na setinha ou no botão 🔄 **Atualizar**).

3. **Tubinho de Cooldown Animado em Cada Tecla (Novo!)**:
   - Cada quadradinho de tecla possui um **tubinho visual** logo abaixo do campo de tempo.
   - Quando você clica em **Iniciar (F6)**, o tubinho começa a encher progressivamente de acordo com o timer configurado (ex: 5 segundos, 500 ms).
   - Ao atingir o máximo (100%), o tubinho clica na tecla correspondente e reinicia o ciclo!
   - Cores intuitivas em tempo real:
     - 🔵 **Azul Elétrico**: Enchendo progressivamente.
     - 🟡 **Dourado / Âmbar**: Em pausa anti-colisão (esperando sua vez para não clicar junto com outra tecla).
     - 🟢 **Verde Vibrante**: Clicou no jogo!
   - Quando parado (**F7**), os tubinhos esvaziam e ficam prontos para o próximo início.

4. **Modo Segundo Plano (Sem roubar foco)**:
   - Envia os comandos de tecla diretamente para o processo do jogo (`PostMessage`) sem roubar seu cursor ou foco da janela.
   - **Ideal para Multitelas**: Deixe o jogo auto-clicando no Monitor 1 enquanto você navega, conversa no Discord ou assiste vídeos no Monitor 2 sem qualquer interrupção!

3. **Modo Foco Ativo (DirectInput / SendInput)**:
   - Para jogos com anti-cheat rigoroso ou tela cheia exclusiva que exigem scancodes de hardware em nível de driver.

4. **Sistema de Salvar & Carregar Setups (Perfis) (Novo!)**:
   - Salve suas configurações com nomes personalizados (ex: *"Farm F10"*, *"Cura Automática"*, *"PVP Rápido"*).
   - O setup salva todas as teclas, seus respectivos timers, unidade de tempo, modo de segundo plano e anti-ban.
   - Dropdown intuitivo para alternar entre diferentes setups com 1 clique.
   - Opção de excluir (`🗑️`) setups antigos quando não precisar mais.

5. **Suporte a Múltiplas Teclas & Timers Independentes**:
   - Cada tecla possui o seu próprio **"quadradinho"** de configuração super intuitivo:
     - **Parte de cima**: Seleção da tecla (`F10`, `F1`, `1`, `SPACE`, etc.).
     - **Parte de baixo**: Campo para digitar o tempo específico dessa tecla (`500 ms`, `2 s`, etc.).
     - **Botão ✕**: Remove a tecla se não quiser mais.
   - Botão **➕ Adicionar Tecla**: Permite adicionar quantos botões você quiser!
   - Cada botão roda de forma simultânea e independente em threads paralelas.

6. **Proteção Anti-Colisão (Nunca Clica Junto) (Novo!)**:
   - Se por acaso os timers de teclas diferentes coincidirem no mesmo instante, o bot **nunca clica as duas juntas**.
   - Ele clica a primeira tecla, dá uma pausa obrigatória de **3 segundos** (ajustável na aba Opções), e em seguida clica a segunda tecla de forma sequencial e segura.

7. **Looping e Timer Configurável**:
   - Ajuste de intervalo em **milissegundos (ms)** ou **segundos (s)**.
   - **Proteção Anti-Ban / Jitter**: Opção de micro-variação humana (±25ms) para evitar padrões robóticos perfeitamente estáticos detectados por anti-cheats.

8. **Atalhos Globais (Hotkeys)**:
   - **F6**: Iniciar
   - **F7**: Parar
   - Funcionam de qualquer lugar: mesmo se você estiver em tela cheia no jogo ou em outra tela.

9. **Painel Flutuante (Always on Top)**:
   - Mantenha a janelinha fixada em um canto da sua tela secundária enquanto joga.
   - Contador de cliques efetuados e tempo decorrido em tempo real.

---

## 🚀 Como Iniciar

Você pode iniciar o projeto com um simples duplo clique:

### Opção 1: Executável Direto .EXE (Recomendado)
Dê um duplo clique no executável independente (não precisa de Python nem terminal):
```text
AutoKeyClicker.exe
```

### Opção 2: Pelo arquivo BAT
```text
iniciar.bat
```

### Opção 3: Pelo código-fonte
```powershell
python main.py
```

---

## 🎮 Passo a Passo para Jogos (ex: Ragnarok Online)

1. Abra o seu jogo normalmente (ex: Ragnarok Online).
2. Abra o **Auto Key Clicker**.
3. Na setinha **1. Janela / Jogo Alvo**, selecione `[ragnarok.exe] Ragnarok Online`.
4. Em **2. Tecla para Clicar Repetidamente**, escolha a tecla desejada (ex: `F10`).
5. Em **3. Intervalo / Tempo de Repetição**, defina o tempo (ex: `500 ms`).
6. Deixe marcado **Modo Segundo Plano** para não atrapalhar seu mouse em outras telas.
7. Pressione o botão verde **INICIAR** ou a tecla **F6** no teclado.
8. Para parar quando quiser, aperte **F7** ou clique em **PARAR**.

---

## 🛡️ Dica Importante sobre Anti-Cheat / Permissões de Administrador

- Se o seu jogo roda como **Administrador** (muito comum em servidores de Ragnarok com Gepard Shield, EAC, Vanguard, etc.), o Windows bloqueia que programas comuns enviem comandos para ele.
- Caso o jogo não responda aos cliques, basta clicar com o botão direito em `iniciar.bat` e selecionar **"Executar como Administrador"**.

---

## 📁 Estrutura do Projeto

- `gui.py`: Interface gráfica moderna dark mode (Tkinter).
- `window_manager.py`: Módulo Win32 para filtrar apenas executáveis reais de primeiro plano.
- `key_sender.py`: Injetor de teclas com mapeamento de Virtual-Keys e ScanCodes (PostMessage e SendInput).
- `clicker_engine.py`: Thread assíncrona do loop de repetição e captura de teclas de atalho globais.
- `main.py` / `iniciar.pyw`: Pontos de entrada do aplicativo.
- `iniciar.bat`: Inicializador direto com 1 clique.
