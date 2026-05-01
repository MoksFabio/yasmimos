<div align="center">
  <br />
  <img src="static/img/logo.png" alt="YasMimos Logo" width="220">
  <br />
  <br />

  <h1 style="font-size: 3em; margin-bottom: 0px;">YasMimos</h1>
  <p style="font-size: 1.2em; color: #666;">
    <i>E-commerce</i>
  </p>

  <br />

  <div style="display: flex; justify-content: center; gap: 10px;">
    <a href="https://www.yasmimos.com.br/">
      <img src="https://img.shields.io/website?down_color=lightgrey&down_message=Offline&label=Status&up_color=4caf50&up_message=Online%20%E2%9C%94&url=https%3A%2F%2Fwww.yasmimos.com.br%2F&style=for-the-badge&logo=google-chrome&logoColor=white" alt="Website Status">
    </a>
    <a href="https://www.instagram.com/yasmimo_s/">
        <img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram">
    </a>
    <a href="https://wa.me/5581983964906">
        <img src="https://img.shields.io/badge/WhatsApp_Bot-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" alt="Whatsapp">
    </a>
  </div>
</div>

<br />

---

## 💡 A Essência do Projeto

O **YasMimos** é um ecossistema de e-commerce completo (Full-Stack) construído do zero, idealizado para gerenciar a venda de doces artesanais no campus da UFPE. Muito mais do que uma vitrine virtual, o projeto resolve problemas reais de logística de vendas físicas, atendimento ao cliente e controle de estoque dinâmico.

Esta aplicação foi rigorosamente projetada aplicando princípios de **Clean Code**, **Arquitetura Modular** (Django MTV) e **Front-End Desacoplado**, servindo como um caso de estudo robusto para sistemas em produção na nuvem (Square Cloud).

---

## ✨ Arquitetura & Features Principais

### 🎨 1. Front-End Modular e Acessível (Sem Frameworks Pesados)
A interface foi construída com **Vanilla CSS e JavaScript puro**, focando em extrema leveza e performance.
* **Desacoplamento UI:** Estilos e lógicas separados em arquivos estáticos específicos por módulo (`auth.css`, `carrinho.css`, etc), mantendo os templates HTML impecáveis.
* **Design System Customizado:** Implementação nativa de **Dark Mode**, temas de alto contraste e fontes especiais para **disléxicos**, garantindo acessibilidade (WCAG).
* **Animações Fluidas:** Uso inteligente de micro-interações (`@keyframes` e flexbox) para guiar o usuário na jornada de compra sem pesar o DOM.

### 🤖 2. Bot de WhatsApp Integrado (Suporte YasMimos)
Um robô autônomo que acompanha o ciclo de vida do pedido.
* **Geração Nativa de Recibos:** O backend possui um motor assíncrono (Pillow) que "desenha" cupons fiscais/recibos dinâmicos em alta fidelidade e os envia ao cliente. (Solução criada para evitar gargalos com browsers headless em ambientes serverless).

### 💬 3. Comunicação em Tempo Real (WebSockets)
* Implementação de chat ao vivo usando **Django Channels e ASGI (Daphne)**.
* Permite que o lojista resolva dúvidas do cliente durante o fechamento do carrinho, diminuindo taxas de abandono.

### 🛍️ 4. Motor de Vendas & Fidelidade
* **Carrinho Avançado:** Suporte a produtos personalizáveis (escolha de slots de sabores).
* **Clube de Assinaturas/Fidelidade:** Sistema restrito com controle de vagas e renovações.
* **Pagamento Automatizado:** Integração transparente com APIs de pagamento (Pix Copia e Cola / QR Code) com baixa automática de status e webhooks.

### 📊 5. Painel Administrativo Moderno
* Dashboard customizada com exportação de dados granulares (ex: relatórios em Excel/XLSX divididos por abas).
* Controle de estoque dinâmico que previne *overbooking* de doces de alta demanda.

---

## 🛠️ Stack Tecnológica

<div align="center">

| Backend & Banco de Dados | Frontend & Design | Infra, DevOps & Integrações |
| :---: | :---: | :---: |
| <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white"> | <img src="https://img.shields.io/badge/HTML5_Semântico-E34F26?style=for-the-badge&logo=html5&logoColor=white"> | <img src="https://img.shields.io/badge/Square_Cloud-000000?style=for-the-badge&logo=cloud&logoColor=white"> |
| <img src="https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"> | <img src="https://img.shields.io/badge/CSS3_Vanilla-1572B6?style=for-the-badge&logo=css3&logoColor=white"> | <img src="https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white"> |
| <img src="https://img.shields.io/badge/Django_Channels-092E20?style=for-the-badge&logo=django&logoColor=white"> | <img src="https://img.shields.io/badge/Vanilla_JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black"> | <img src="https://img.shields.io/badge/Pillow_(Image_Gen)-3776AB?style=for-the-badge&logo=python&logoColor=white"> |

</div>

<br>

<details>
<summary>📂 <strong>Estrutura de Módulos (Arquitetura)</strong></summary>
<br>

O projeto respeita o padrão **MTV (Model-Template-View)** particionado em apps independentes:

*   `produtos/`: Motor do catálogo, controle de estoque e avaliações.
*   `carrinho/` & `pedidos/`: Lógica de checkout, carrinho de sessão e histórico.
*   `usuarios/` & `fidelidade/`: Gestão de contas, autenticação segura e gamificação.
*   `robo_whatsapp/`: A interface do Bot YasMimos e o motor de renderização de recibos.
*   `chat/`: O barramento de comunicação WebSocket.
*   `static/`: Contém a nova arquitetura modular de CSS e JS isolada por páginas.

</details>

---

## 📸 Projeto Online

Sinta a experiência fluida da plataforma interagindo com a versão de produção.

<div align="center">
  <br>
  <a href="https://www.yasmimos.com.br/">
    <img src="https://img.shields.io/badge/✨_ACESSAR_E--COMMERCE_✨-ff69b4?style=for-the-badge&logo=google-chrome&logoColor=white" height="40">
  </a>
</div>

---

<div align="center">
  <br>
  <p>Não espere pelo amanhã para criar algo que possa mudar o hoje.</p>
</div>
