require('dotenv').config({ path: '../.env' }); // Lê o arquivo .env da raiz do projeto
const { IgApiClient } = require('instagram-private-api');
const http = require('http');

async function connectToInstagram() {
    const ig = new IgApiClient();

    const username = process.env.IG_USERNAME;
    const password = process.env.IG_PASSWORD;
    const sessionId = process.env.IG_SESSIONID;
    const csrfToken = process.env.IG_CSRFTOKEN || "missing_csrf";

    if (!username) {
        console.error("❌ ERRO: IG_USERNAME não foi configurado no arquivo de ambiente");
        return;
    }

    ig.state.generateDevice(username);

    if (sessionId) {
        console.log("Usando Session ID e CSRF Token para pular a tela de login...");
        try {
            const userId = sessionId.split('%3A')[0];
            const cookieStr = JSON.stringify({
                "cookies": [
                    {
                        "key": "sessionid",
                        "value": sessionId,
                        "domain": "i.instagram.com",
                        "path": "/",
                        "hostOnly": false,
                        "creation": new Date().toISOString(),
                        "lastAccessed": new Date().toISOString()
                    },
                    {
                        "key": "csrftoken",
                        "value": csrfToken,
                        "domain": "i.instagram.com",
                        "path": "/",
                        "hostOnly": false,
                        "creation": new Date().toISOString(),
                        "lastAccessed": new Date().toISOString()
                    },
                    {
                        "key": "ds_user_id",
                        "value": userId,
                        "domain": "i.instagram.com",
                        "path": "/",
                        "hostOnly": false,
                        "creation": new Date().toISOString(),
                        "lastAccessed": new Date().toISOString()
                    }
                ]
            });
            await ig.state.deserializeCookieJar(cookieStr);
            ig.state.cookieUserId = userId; // Define o ID de usuário a partir do cookie
            console.log('✅ Bot conectado ao Instagram (via Cookie) com sucesso! Aguardando mensagens...');
        } catch (e) {
            console.error("❌ Falha ao restaurar sessão por Cookie.", e.message);
            return;
        }
    } else {
        if (!password) {
            console.error("❌ ERRO: IG_PASSWORD não configurado (e nenhum Session ID foi fornecido).");
            return;
        }
        // Tenta fazer o login
        try {
            console.log(`Tentando login no Instagram com a conta: ${username}...`);
            await ig.account.login(username, password);
            console.log('✅ Bot conectado ao Instagram com sucesso! Aguardando mensagens...');
        } catch (e) {
            console.error("❌ Falha ao fazer login no Instagram. Verifique se as credenciais estão corretas ou se o Instagram não bloqueou o acesso exigindo verificação por e-mail/SMS.", e.message);
            return;
        }
    }

    // Memória para controlar o estado do usuário
    const userStates = new Map();
    const welcomeSent = new Map(); // Guarda quando a última saudação completa foi enviada
    const lastMessageIdProcessed = new Set(); // Para não processar a mesma mensagem duas vezes
    
    const HUMAN_TIMEOUT_MS = 60 * 60 * 1000; // 1 hora de pausa
    const MENU_TIMEOUT_MS = 10 * 60 * 1000; // 10 min de inatividade volta pro inicio

    // Monitor de Inatividade (10 minutos)
    setInterval(async () => {
        const now = Date.now();
        for (const [threadId, userData] of userStates.entries()) {
            if (userData.state === 'HUMAN' || userData.state === 'START') continue;

            if (now - userData.lastActivity > MENU_TIMEOUT_MS) {
                try {
                    const thread = ig.entity.directThread(threadId);
                    await thread.broadcastText("Poxa, parece que você deu uma saidinha! 🏃💨\n\nPor inatividade, vou encerrar nosso chat por agora. Se precisar de algo, é só mandar uma nova mensagem! ✨");
                    userStates.delete(threadId);
                    welcomeSent.delete(threadId);
                } catch (e) {
                    // Silencioso se der erro no envio
                }
            }
        }
    }, 60000); // Checa a cada 1 minuto

    function fetchApi(path) {
        return new Promise((resolve, reject) => {
            http.get(`http://127.0.0.1${path}`, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try { resolve(JSON.parse(data)); }
                    catch (e) { reject(e); }
                });
            }).on('error', err => reject(err));
        });
    }

    // POLLING: Lê as mensagens a cada 5 segundos
    setInterval(async () => {
        try {
            const inboxFeed = ig.feed.directInbox();
            const threads = await inboxFeed.items();

            for (const thread of threads) {
                // A primeira mensagem da thread é a mais recente
                const lastMessage = thread.items[0];
                
                // Se a mensagem for nossa (do próprio bot), ignoramos
                if (lastMessage.user_id === ig.state.cookieUserId) continue;

                // Se já processamos essa mensagem, pulamos
                if (lastMessageIdProcessed.has(lastMessage.item_id)) continue;
                
                // Marca como lida e processada
                lastMessageIdProcessed.add(lastMessage.item_id);
                // Opcional: Para evitar que a lista de ids fique gigante na memória
                if (lastMessageIdProcessed.size > 1000) {
                    const firstItem = lastMessageIdProcessed.values().next().value;
                    lastMessageIdProcessed.delete(firstItem);
                }

                // Marca a thread como visualizada no app
                await ig.entity.directThread(thread.thread_id).markItemSeen(lastMessage.item_id);

                const threadId = thread.thread_id;
                
                let textMessage = "";
                if (lastMessage.item_type === 'text') {
                    textMessage = lastMessage.text;
                } else if (lastMessage.item_type === 'link') {
                    textMessage = lastMessage.link.text;
                } else {
                    // Ignora áudios, imagens, etc, no momento.
                    continue; 
                }

                if (textMessage) {
                    const now = Date.now();
                    let userData = userStates.get(threadId) || { state: 'START', lastActivity: 0, lastMessageTime: 0 };

                    // ANTI-SPAM
                    if (now - userData.lastMessageTime < 1500) {
                        continue;
                    }
                    userData.lastMessageTime = now;

                    const activeThread = ig.entity.directThread(threadId);

                    // PROTEÇÃO DE TAMANHO
                    if (textMessage.length > 500) {
                        await activeThread.broadcastText("Ops! Sua mensagem é muito longa. Por favor, tente algo mais curto! ✨");
                        continue;
                    }

                    const textStr = textMessage.trim();
                    const menuOpcoes = `*1* 🛒 Fazer um pedido\n` +
                        `*2* 📦 Status do pedido\n` +
                        `*3* 📖 Ver catálogo\n` +
                        `*4* 📍 Horários e Endereço\n` +
                        `*5* ❓ Dúvidas Frequentes\n` +
                        `*6* 💖 Pontos de Fidelidade\n` +
                        `*7* 👩‍💼 Falar com um atendente\n` +
                        `*8* 🏁 Encerrar atendimento`;

                    if (!userData.state || (now - userData.lastActivity > MENU_TIMEOUT_MS && userData.state !== 'HUMAN')) {
                        userData.state = 'START';
                        userData.lastActivity = now;
                    }

                    if (userData.state === 'HUMAN') {
                        if (textStr === '0') {
                            userData.state = 'START';
                            welcomeSent.delete(threadId);
                        } else if (now - userData.lastActivity > HUMAN_TIMEOUT_MS) {
                            userData.state = 'START';
                        } else {
                            userData.lastActivity = now;
                            userStates.set(threadId, userData);
                            continue;
                        }
                    }

                    userData.lastActivity = now;
                    userStates.set(threadId, userData);

                    // Simulando o "digitando..."
                    await activeThread.broadcastAction('typing_on');
                    await new Promise(r => setTimeout(r, 1500));
                    await activeThread.broadcastAction('typing_off');

                    try {
                        if (/^[1-8]$/.test(textStr)) {
                            if (userData.state === 'AWAITING_REVIEW' && /^[1-5]$/.test(textStr)) {
                            } else if (userData.state === 'AWAITING_ORDER_ID') {
                            } else {
                                userData.state = 'MENU';
                            }
                        }

                        if (userData.state === 'START') {
                            const apiInfo = await fetchApi('/sistema/api/bot/info/');
                            const lastWelcome = welcomeSent.get(threadId) || 0;
                            const isRecent = (now - lastWelcome < 10 * 60 * 1000);

                            if (isRecent) {
                                await activeThread.broadcastText(`Como posso te ajudar agora? ✨\n\n${menuOpcoes}`);
                            } else {
                                welcomeSent.set(threadId, now);
                                let statusText = apiInfo.is_open
                                    ? `🟢 *Estamos ABERTOS!*\n${apiInfo.details || ""}`
                                    : `🔴 *Estamos FECHADOS no momento.*\n${apiInfo.notice || ""}`;

                                const msgMenu = `Olá! Aqui é o atendimento virtual da *YasMimos*! 🧁✨\n\n` +
                                    `${statusText.trim()}\n\n` +
                                    `Como posso te ajudar hoje? Digite o *número* da opção desejada:\n\n${menuOpcoes}`;

                                await activeThread.broadcastText(msgMenu);
                            }
                            userData.state = 'MENU';
                            userStates.set(threadId, userData);
                            continue;
                        }
                        else if (userData.state === 'AWAITING_FIDELITY_ID') {
                            if (textStr === '0') {
                                userData.state = 'MENU';
                                await activeThread.broadcastText(`Voltando ao menu principal... ✨\n\n${menuOpcoes}`);
                                userStates.set(threadId, userData);
                                continue;
                            } else {
                                try {
                                    const fidelity = await fetchApi(`/sistema/api/bot/fidelity/${encodeURIComponent(textStr)}/`);
                                    if (fidelity.status === 'success') {
                                        const stamps = fidelity.stamps;
                                        let motivacao = "";
                                        if (stamps === 0) motivacao = "Sua jornada de mimos começa aqui! Que tal garantir seu primeiro selo hoje? 🥰";
                                        else if (stamps <= 3) motivacao = "Você já começou a colecionar felicidade! Continue assim, cada caixinha te deixa mais perto do seu presente! 🍫";
                                        else if (stamps <= 5) motivacao = "Uau! Você já é de casa! Falta muito pouco para você ganhar sua recompensa. Não para agora! 🔥";
                                        else if (stamps === 6) motivacao = "SÓ FALTA UM! No próximo pedido você completa seu cartão e ganha seu mimo! Estamos torcendo por você! 🎉🧁";

                                        const msgFid = `💖 *Cartão de ${fidelity.customer_name}*\n\n` +
                                            `✅ Você tem: *${stamps} selos*\n` +
                                            `🎁 Faltam: *${fidelity.missing} selos* para o prêmio!\n\n` +
                                            `${motivacao}\n\n` +
                                            `*Deseja consultar outro ID?* Digite o ID abaixo.\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada):\n\n${menuOpcoes}`;

                                        await activeThread.broadcastText(msgFid);
                                        userData.state = 'AWAITING_FIDELITY_ID';
                                        userStates.set(threadId, userData);
                                        continue;
                                    } else {
                                        await activeThread.broadcastText("❌ Não encontrei nenhum cartão com esse ID. Verifique se digitou corretamente e *tente novamente*, ou digite *0* para voltar ao menu principal. ✨");
                                        continue;
                                    }
                                } catch (e) {
                                    await activeThread.broadcastText("Houve um erro ao consultar o cartão. Tente novamente mais tarde.");
                                    continue;
                                }
                            }
                        }
                        else if (userData.state === 'AWAITING_FAQ') {
                            const choice = textStr.toUpperCase();
                            if (choice === '0') {
                                userData.state = 'MENU';
                                await activeThread.broadcastText(`Voltando ao menu principal... ✨\n\n${menuOpcoes}`);
                                userStates.set(threadId, userData);
                                continue;
                            } else if (choice === 'A') {
                                await activeThread.broadcastText("💳 *Formas de Pagamento:*\n\nAceitamos PIX (direto no site), Cartão de Crédito/Débito (via link ou na retirada) e Dinheiro.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes);
                                userData.state = 'MENU';
                            } else if (choice === 'B') {
                                await activeThread.broadcastText("🎨 *Personalização:*\n\nApenas a *Caixinha da Felicidade Personalizada* permite a escolha de sabores. Você escolhe os 4 brigadeiros diretamente no nosso site!\n\n⏳ *Tempo de Preparo:* Por ser uma encomenda artesanal, seu pedido será preparado em alguns dias após a confirmação. O tempo exato depende dos dias em que estivermos abertos (confira sempre o status no topo da conversa!). ✨\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes);
                                userData.state = 'MENU';
                            } else if (choice === 'C') {
                                await activeThread.broadcastText("🛵 *Entrega e Retirada:*\n\nAtualmente focamos em retiradas no Centro de Biociências (CB). Para entregas em outros locais, consulte a disponibilidade com um atendente.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes);
                                userData.state = 'MENU';
                            } else {
                                await activeThread.broadcastText("Ops! Escolha A, B ou C, ou digite 0 para voltar ao menu principal.");
                                continue;
                            }
                        }
                        else if (userData.state === 'AWAITING_REVIEW') {
                            await activeThread.broadcastText("Recebemos sua avaliação! Muito obrigado pelo feedback, ele nos ajuda a melhorar sempre. 🥰\n\nTenha um mimoso dia! ✨");
                            userData.state = 'START';
                            welcomeSent.delete(threadId);
                            userStates.set(threadId, userData);
                            continue;
                        }
                        else if (userData.state === 'AWAITING_ORDER_ID') {
                            const orderIdStr = textStr.replace(/\D/g, '');
                            if (orderIdStr === '0' || orderIdStr === '') {
                                userData.state = 'MENU';
                                await activeThread.broadcastText(`Voltando ao menu principal... ✨\n\n${menuOpcoes}`);
                                userStates.set(threadId, userData);
                                continue;
                            }
                            const orderId = parseInt(orderIdStr, 10);
                            try {
                                const botToken = process.env.TELEGRAM_BOT_TOKEN || '';
                                const orderInfo = await fetchApi(`/sistema/api/bot/order/${orderId}/?bot_token=${botToken}`);
                                if (orderInfo.status === 'success') {
                                    const captionText = `📦 *Status do Pedido #${orderInfo.order_id}*\n\n` +
                                        `Status atual: *${orderInfo.status_display}*\n` +
                                        `Valor Total: R$ ${orderInfo.total.toFixed(2).replace('.', ',')}\n\n` +
                                        `Para ver o comprovante detalhado acesse o WhatsApp ou o site!\n\n` +
                                        `*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada):\n\n${menuOpcoes}`;
                                        
                                    // A API privada do Instagram não suporta envio fácil de imagens por URL como o WhatsApp, enviamos apenas texto
                                    await activeThread.broadcastText(captionText);
                                    
                                    userData.state = 'MENU';
                                    userStates.set(threadId, userData);
                                    continue;
                                } else {
                                    await activeThread.broadcastText(`❌ Não consegui encontrar o pedido #${orderId}. Verifique se o número está correto.\n(Digite 0 para voltar ao menu)`);
                                    continue;
                                }
                            } catch (e) {
                                await activeThread.broadcastText(`❌ Houve um erro ao buscar o pedido #${orderId}.\n(Digite 0 para voltar ao menu)`);
                                continue;
                            }
                        }

                        // BLOCO FINAL DO MENU: Processa 1 a 8
                        if (userData.state === 'MENU') {
                            if (textStr === '1') {
                                const apiInfo = await fetchApi('/sistema/api/bot/info/');
                                let msgResposta = `Nossos pedidos são feitos diretamente pelo nosso site! Lá você encontra nosso cardápio completo.\n\n🌐 *Acesse:* https://www.yasmimos.com.br/`;
                                if (!apiInfo.is_open) {
                                    msgResposta += `\n\n⚠️ *Atenção:* ${apiInfo.notice || "Estamos fechados agora, mas você pode conferir o cardápio!"}`;
                                }
                                msgResposta += `\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`;
                                await activeThread.broadcastText(msgResposta);
                            }
                            else if (textStr === '2') {
                                await activeThread.broadcastText("Por favor, digite apenas o *número do seu pedido* (ex: 123) ou *0* para voltar ao menu:");
                                userData.state = 'AWAITING_ORDER_ID';
                            }
                            else if (textStr === '3') {
                                await activeThread.broadcastText("Buscando nosso cardápio completo... ⏳🧁");
                                try {
                                    const prodData = await fetchApi(`/sistema/api/bot/products/all/`);
                                    if (prodData.products && prodData.products.length > 0) {
                                        for (let p of prodData.products) {
                                            const caption = `🍫 *${p.name}*\n💰 R$ ${p.price.toFixed(2).replace('.', ',')}\n📦 Estoque: ${p.stock} unidades\n\n👉 *Ver no site:* ${p.url}`;
                                            await activeThread.broadcastText(caption);
                                            await new Promise(r => setTimeout(r, 800));
                                        }
                                        await activeThread.broadcastText(`Acima estão os nossos mimos disponíveis! ✨\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`);
                                    } else {
                                        await activeThread.broadcastText(`No momento não temos produtos disponíveis no catálogo online.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`);
                                    }
                                } catch (e) {
                                    await activeThread.broadcastText("Houve um erro ao carregar o catálogo. Tente novamente mais tarde.");
                                }
                            }
                            else if (textStr === '4') {
                                const apiInfo = await fetchApi('/sistema/api/bot/info/');
                                let msgResposta = `*📍 Informações de Retirada/Entrega:*\n\n${apiInfo.notice || 'Sem avisos no momento.'}\n`;
                                if (apiInfo.details) {
                                    msgResposta += `\n*Detalhes:*\n${apiInfo.details}`;
                                }
                                msgResposta += `\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`;
                                await activeThread.broadcastText(msgResposta);
                            }
                            else if (textStr === '5') {
                                const faqMsg = `❓ *Dúvidas Frequentes:*\n\n` +
                                    `*A* - Quais as formas de pagamento?\n` +
                                    `*B* - Como personalizar meu pedido?\n` +
                                    `*C* - Como funciona a retirada?\n\n` +
                                    `*0* - Voltar ao menu principal`;
                                await activeThread.broadcastText(faqMsg);
                                userData.state = 'AWAITING_FAQ';
                            }
                            else if (textStr === '6') {
                                await activeThread.broadcastText("🧁 *Cartão Fidelidade YasMimos*\n\nA cada *Caixinha da Felicidade* você ganha 1 selo! (Independente de ser personalizada ou não). 🎁\n\nAo completar *7 selos*, você ganha uma recompensa deliciosa!\n\nPara consultar seus pontos, por favor, digite o *ID do seu cartão* (Ex: Tassia) ou digite *0* para voltar ao menu:");
                                userData.state = 'AWAITING_FIDELITY_ID';
                            }
                            else if (textStr === '7') {
                                await activeThread.broadcastText("Certo! O seu atendimento foi transferido para um humano. 👩‍💼\n\nNossa equipe te responderá o mais rápido possível por aqui mesmo.\n\n_(Para encerrar o atendimento humano e voltar pro menu automático, digite *0*)_");
                                userData.state = 'HUMAN';
                            }
                            else if (textStr === '8') {
                                await activeThread.broadcastText("Obrigado por entrar em contato com a *YasMimos*! 🧁✨\n\nAntes de ir, como você avalia nosso atendimento hoje?\n\n*5* - Excelente ⭐\n*4* - Muito Bom\n*3* - Bom\n*2* - Regular\n*1* - Ruim");
                                userData.state = 'AWAITING_REVIEW';
                            }
                            else {
                                await activeThread.broadcastText(`Ops! Não entendi essa opção... 🤔\n\nPor favor, escolha uma das opções abaixo (1 a 8):\n\n${menuOpcoes}`);
                            }
                        }

                        userStates.set(threadId, userData);

                    } catch (err) {
                        console.error("Erro na integração com a API: ", err);
                    }
                }
            }
        } catch (error) {
            console.error("Erro ao verificar mensagens no Instagram:", error.message);
        }
    }, 5000); // Polling a cada 5 segundos
}

connectToInstagram();
