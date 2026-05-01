require('dotenv').config({ path: '../.env' });
const https = require('https');
const http = require('http');
const crypto = require('crypto');

async function connectToInstagram() {
    const sessionId = process.env.IG_SESSIONID;
    const csrfToken = process.env.IG_CSRFTOKEN;
    
    if (!sessionId || !csrfToken) {
        console.error("❌ ERRO: Para o bot Web API rodar, IG_SESSIONID e IG_CSRFTOKEN devem estar configurados.");
        return;
    }

    const userId = sessionId.split('%3A')[0];
    console.log("Iniciando Bot do Instagram via Web API Hack... ID: " + userId);

    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459',
        'X-CSRFToken': csrfToken,
        'Cookie': `sessionid=${sessionId}; csrftoken=${csrfToken}; ds_user_id=${userId};`
    };

    function fetchIg(url, method = 'GET', bodyStr = null) {
        return new Promise((resolve, reject) => {
            const urlObj = new URL(url);
            const options = {
                hostname: urlObj.hostname,
                path: urlObj.pathname + urlObj.search,
                method: method,
                headers: { ...headers }
            };
            if (bodyStr) {
                options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                options.headers['Content-Length'] = Buffer.byteLength(bodyStr);
            }

            const req = https.request(options, (res) => {
                let data = '';
                res.on('data', d => data += d);
                res.on('end', () => {
                    if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                    try { resolve(JSON.parse(data)); } catch(e) { resolve(data); }
                });
            });
            req.on('error', reject);
            if (bodyStr) req.write(bodyStr);
            req.end();
        });
    }

    async function broadcastText(threadId, text) {
        const clientContext = crypto.randomUUID();
        const body = `text=${encodeURIComponent(text)}&client_context=${clientContext}`;
        await fetchIg(`https://www.instagram.com/api/v1/direct_v2/threads/${threadId}/broadcast/text/`, 'POST', body);
    }
    
    // Teste de Conexão
    try {
        await fetchIg('https://www.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=0&limit=10');
        console.log('✅ Bot conectado ao Instagram (via Web API) com sucesso! Aguardando mensagens...');
    } catch(e) {
        console.error("❌ Falha crítica ao conectar Web API:", e.message);
        return;
    }

    const userStates = new Map();
    const welcomeSent = new Map();
    const lastMessageIdProcessed = new Set();
    
    const HUMAN_TIMEOUT_MS = 60 * 60 * 1000;
    const MENU_TIMEOUT_MS = 10 * 60 * 1000;

    setInterval(async () => {
        const now = Date.now();
        for (const [threadId, userData] of userStates.entries()) {
            if (userData.state === 'HUMAN' || userData.state === 'START') continue;
            if (now - userData.lastActivity > MENU_TIMEOUT_MS) {
                try {
                    await broadcastText(threadId, "Poxa, parece que você deu uma saidinha! 🏃💨\n\nPor inatividade, vou encerrar nosso chat por agora. Se precisar de algo, é só mandar uma nova mensagem! ✨");
                    userStates.delete(threadId);
                    welcomeSent.delete(threadId);
                } catch (e) {}
            }
        }
    }, 60000);

    function fetchApi(path) {
        return new Promise((resolve, reject) => {
            http.get(`http://127.0.0.1${path}`, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
                });
            }).on('error', reject);
        });
    }

    // POLLING: Lê mensagens a cada 5 segundos
    setInterval(async () => {
        try {
            const inbox = await fetchIg('https://www.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=0&limit=10');
            const threads = inbox.inbox.threads;

            for (const thread of threads) {
                const lastMessage = thread.items[0];
                if (!lastMessage) continue;
                
                // Ignora se fomos nós que enviamos
                if (String(lastMessage.user_id) === String(userId)) continue;
                
                if (lastMessageIdProcessed.has(lastMessage.item_id)) continue;
                lastMessageIdProcessed.add(lastMessage.item_id);
                if (lastMessageIdProcessed.size > 1000) {
                    const firstItem = lastMessageIdProcessed.values().next().value;
                    lastMessageIdProcessed.delete(firstItem);
                }

                // Marca como lida
                try {
                    const clientContext = crypto.randomUUID();
                    await fetchIg(`https://www.instagram.com/api/v1/direct_v2/threads/${thread.thread_id}/items/${lastMessage.item_id}/seen/`, 'POST', `client_context=${clientContext}`);
                } catch(e) {}

                const threadId = thread.thread_id;
                
                let textMessage = "";
                if (lastMessage.item_type === 'text') {
                    textMessage = lastMessage.text;
                } else if (lastMessage.item_type === 'link') {
                    textMessage = lastMessage.link.text;
                } else {
                    continue; 
                }

                if (textMessage) {
                    const now = Date.now();
                    let userData = userStates.get(threadId) || { state: 'START', lastActivity: 0, lastMessageTime: 0 };

                    if (now - userData.lastMessageTime < 1500) continue;
                    userData.lastMessageTime = now;

                    if (textMessage.length > 500) {
                        await broadcastText(threadId, "Ops! Sua mensagem é muito longa. Por favor, tente algo mais curto! ✨");
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
                                await broadcastText(threadId, `Como posso te ajudar agora? ✨\n\n${menuOpcoes}`);
                            } else {
                                welcomeSent.set(threadId, now);
                                let statusText = apiInfo.is_open
                                    ? `🟢 *Estamos ABERTOS!*\n${apiInfo.details || ""}`
                                    : `🔴 *Estamos FECHADOS no momento.*\n${apiInfo.notice || ""}`;

                                const msgMenu = `Olá! Aqui é o atendimento virtual da *YasMimos*! 🧁✨\n\n` +
                                    `${statusText.trim()}\n\n` +
                                    `Como posso te ajudar hoje? Digite o *número* da opção desejada:\n\n${menuOpcoes}`;

                                await broadcastText(threadId, msgMenu);
                            }
                            userData.state = 'MENU';
                            userStates.set(threadId, userData);
                            continue;
                        }
                        else if (userData.state === 'AWAITING_FIDELITY_ID') {
                            if (textStr === '0') {
                                userData.state = 'MENU';
                                await broadcastText(threadId, `Voltando ao menu principal... ✨\n\n${menuOpcoes}`);
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

                                        await broadcastText(threadId, msgFid);
                                        userData.state = 'AWAITING_FIDELITY_ID';
                                        userStates.set(threadId, userData);
                                        continue;
                                    } else {
                                        await broadcastText(threadId, "❌ Não encontrei nenhum cartão com esse ID. Verifique se digitou corretamente e *tente novamente*, ou digite *0* para voltar ao menu principal. ✨");
                                        continue;
                                    }
                                } catch (e) {
                                    await broadcastText(threadId, "Houve um erro ao consultar o cartão. Tente novamente mais tarde.");
                                    continue;
                                }
                            }
                        }
                        else if (userData.state === 'AWAITING_FAQ') {
                            const choice = textStr.toUpperCase();
                            if (choice === '0') {
                                userData.state = 'MENU';
                                await broadcastText(threadId, `Voltando ao menu principal... ✨\n\n${menuOpcoes}`);
                                userStates.set(threadId, userData);
                                continue;
                            } else if (choice === 'A') {
                                await broadcastText(threadId, "💳 *Formas de Pagamento:*\n\nAceitamos PIX (direto no site), Cartão de Crédito/Débito (via link ou na retirada) e Dinheiro.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes);
                                userData.state = 'MENU';
                            } else if (choice === 'B') {
                                await broadcastText(threadId, "🎨 *Personalização:*\n\nApenas a *Caixinha da Felicidade Personalizada* permite a escolha de sabores. Você escolhe os 4 brigadeiros diretamente no nosso site!\n\n⏳ *Tempo de Preparo:* Por ser uma encomenda artesanal, seu pedido será preparado em alguns dias após a confirmação. O tempo exato depende dos dias em que estivermos abertos (confira sempre o status no topo da conversa!). ✨\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes);
                                userData.state = 'MENU';
                            } else if (choice === 'C') {
                                await broadcastText(threadId, "🛵 *Entrega e Retirada:*\n\nAtualmente focamos em retiradas no Centro de Biociências (CB). Para entregas em outros locais, consulte a disponibilidade com um atendente.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes);
                                userData.state = 'MENU';
                            } else {
                                await broadcastText(threadId, "Ops! Escolha A, B ou C, ou digite 0 para voltar ao menu principal.");
                                continue;
                            }
                        }
                        else if (userData.state === 'AWAITING_REVIEW') {
                            await broadcastText(threadId, "Recebemos sua avaliação! Muito obrigado pelo feedback, ele nos ajuda a melhorar sempre. 🥰\n\nTenha um mimoso dia! ✨");
                            userData.state = 'START';
                            welcomeSent.delete(threadId);
                            userStates.set(threadId, userData);
                            continue;
                        }
                        else if (userData.state === 'AWAITING_ORDER_ID') {
                            const orderIdStr = textStr.replace(/\D/g, '');
                            if (orderIdStr === '0' || orderIdStr === '') {
                                userData.state = 'MENU';
                                await broadcastText(threadId, `Voltando ao menu principal... ✨\n\n${menuOpcoes}`);
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
                                        `Para ver o comprovante acesse o WhatsApp ou Site!\n\n` +
                                        `*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada):\n\n${menuOpcoes}`;
                                        
                                    await broadcastText(threadId, captionText);
                                    userData.state = 'MENU';
                                    userStates.set(threadId, userData);
                                    continue;
                                } else {
                                    await broadcastText(threadId, `❌ Não consegui encontrar o pedido #${orderId}. Verifique se o número está correto.\n(Digite 0 para voltar ao menu)`);
                                    continue;
                                }
                            } catch (e) {
                                await broadcastText(threadId, `❌ Houve um erro ao buscar o pedido #${orderId}.\n(Digite 0 para voltar ao menu)`);
                                continue;
                            }
                        }

                        if (userData.state === 'MENU') {
                            if (textStr === '1') {
                                const apiInfo = await fetchApi('/sistema/api/bot/info/');
                                let msgResposta = `Nossos pedidos são feitos diretamente pelo nosso site! Lá você encontra nosso cardápio completo.\n\n🌐 *Acesse:* https://www.yasmimos.com.br/`;
                                if (!apiInfo.is_open) {
                                    msgResposta += `\n\n⚠️ *Atenção:* ${apiInfo.notice || "Estamos fechados agora, mas você pode conferir o cardápio!"}`;
                                }
                                msgResposta += `\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`;
                                await broadcastText(threadId, msgResposta);
                            }
                            else if (textStr === '2') {
                                await broadcastText(threadId, "Por favor, digite apenas o *número do seu pedido* (ex: 123) ou *0* para voltar ao menu:");
                                userData.state = 'AWAITING_ORDER_ID';
                            }
                            else if (textStr === '3') {
                                await broadcastText(threadId, "Buscando nosso cardápio completo... ⏳🧁");
                                try {
                                    const prodData = await fetchApi(`/sistema/api/bot/products/all/`);
                                    if (prodData.products && prodData.products.length > 0) {
                                        for (let p of prodData.products) {
                                            const caption = `🍫 *${p.name}*\n💰 R$ ${p.price.toFixed(2).replace('.', ',')}\n📦 Estoque: ${p.stock} unidades\n\n👉 *Ver no site:* ${p.url}`;
                                            await broadcastText(threadId, caption);
                                            await new Promise(r => setTimeout(r, 800));
                                        }
                                        await broadcastText(threadId, `Acima estão os nossos mimos disponíveis! ✨\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`);
                                    } else {
                                        await broadcastText(threadId, `No momento não temos produtos disponíveis no catálogo online.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`);
                                    }
                                } catch (e) {
                                    await broadcastText(threadId, "Houve um erro ao carregar o catálogo. Tente novamente mais tarde.");
                                }
                            }
                            else if (textStr === '4') {
                                const apiInfo = await fetchApi('/sistema/api/bot/info/');
                                let msgResposta = `*📍 Informações de Retirada/Entrega:*\n\n${apiInfo.notice || 'Sem avisos no momento.'}\n`;
                                if (apiInfo.details) {
                                    msgResposta += `\n*Detalhes:*\n${apiInfo.details}`;
                                }
                                msgResposta += `\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`;
                                await broadcastText(threadId, msgResposta);
                            }
                            else if (textStr === '5') {
                                const faqMsg = `❓ *Dúvidas Frequentes:*\n\n` +
                                    `*A* - Quais as formas de pagamento?\n` +
                                    `*B* - Como personalizar meu pedido?\n` +
                                    `*C* - Como funciona a retirada?\n\n` +
                                    `*0* - Voltar ao menu principal`;
                                await broadcastText(threadId, faqMsg);
                                userData.state = 'AWAITING_FAQ';
                            }
                            else if (textStr === '6') {
                                await broadcastText(threadId, "🧁 *Cartão Fidelidade YasMimos*\n\nA cada *Caixinha da Felicidade* você ganha 1 selo! (Independente de ser personalizada ou não). 🎁\n\nAo completar *7 selos*, você ganha uma recompensa deliciosa!\n\nPara consultar seus pontos, por favor, digite o *ID do seu cartão* (Ex: Tassia) ou digite *0* para voltar ao menu:");
                                userData.state = 'AWAITING_FIDELITY_ID';
                            }
                            else if (textStr === '7') {
                                await broadcastText(threadId, "Certo! O seu atendimento foi transferido para um humano. 👩‍💼\n\nNossa equipe te responderá o mais rápido possível por aqui mesmo.\n\n_(Para encerrar o atendimento humano e voltar pro menu automático, digite *0*)_");
                                userData.state = 'HUMAN';
                            }
                            else if (textStr === '8') {
                                await broadcastText(threadId, "Obrigado por entrar em contato com a *YasMimos*! 🧁✨\n\nAntes de ir, como você avalia nosso atendimento hoje?\n\n*5* - Excelente ⭐\n*4* - Muito Bom\n*3* - Bom\n*2* - Regular\n*1* - Ruim");
                                userData.state = 'AWAITING_REVIEW';
                            }
                            else {
                                await broadcastText(threadId, `Ops! Não entendi essa opção... 🤔\n\nPor favor, escolha uma das opções abaixo (1 a 8):\n\n${menuOpcoes}`);
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
    }, 5000);
}

connectToInstagram();
