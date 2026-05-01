const pino = require('pino');

async function connectToWhatsApp() {
    // Import dinâmico necessário para a versão mais recente do Baileys (ESM)
    const baileys = await import('@whiskeysockets/baileys');
    const makeWASocket = baileys.default.default || baileys.default;
    const { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = baileys;

    // O auth_info_baileys vai salvar a sessão (QR Code não será necessário toda vez)
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');

    // Pega a versão mais recente do WhatsApp Web (Resolve os erros 405 Connection Failure)
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`Usando WhatsApp Web versão v${version.join('.')}, isLatest: ${isLatest}`);

    const sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' }) // Mantém o terminal limpo de logs desnecessários
    });

    // Salva as credenciais sempre que houver uma atualização
    sock.ev.on('creds.update', saveCreds);

    // Monitora a conexão
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            // Usa o qrcode-terminal para mostrar o código na tela, pois o Baileys descontinuou a versão nativa
            const qrcode = require('qrcode-terminal');
            qrcode.generate(qr, { small: true });
            console.log('👆 LEIA O QR CODE ACIMA COM O SEU WHATSAPP!');
        }

        if (connection === 'close') {
            const shouldReconnect = lastDisconnect.error?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('Conexão fechada devido a ', lastDisconnect.error, ', reconectando: ', shouldReconnect);
            if (shouldReconnect) {
                connectToWhatsApp();
            } else {
                console.log('Você foi desconectado. Apague a pasta auth_info_baileys e rode o bot novamente para ler o QR Code.');
            }
        } else if (connection === 'open') {
            console.log('✅ Bot conectado ao WhatsApp com sucesso! Aguardando mensagens...');
        }
    });

    // Memória para controlar o estado do usuário
    const userStates = new Map();
    const welcomeSent = new Map(); // Guarda quando a última saudação completa foi enviada
    const HUMAN_TIMEOUT_MS = 60 * 60 * 1000; // 1 hora de pausa
    const MENU_TIMEOUT_MS = 10 * 60 * 1000; // 10 min de inatividade volta pro inicio

    // Monitor de Inatividade (10 minutos)
    setInterval(async () => {
        const now = Date.now();
        for (const [remoteId, userData] of userStates.entries()) {
            // Não encerra se estiver com humano ou se acabou de começar
            if (userData.state === 'HUMAN' || userData.state === 'START') continue;

            if (now - userData.lastActivity > MENU_TIMEOUT_MS) {
                try {
                    await sock.sendMessage(remoteId, { text: "Poxa, parece que você deu uma saidinha! 🏃💨\n\nPor inatividade, vou encerrar nosso chat por agora. Se precisar de algo, é só mandar uma nova mensagem! ✨" });
                    userStates.delete(remoteId);
                    welcomeSent.delete(remoteId);
                } catch (e) {
                    // Silencioso se der erro no envio
                }
            }
        }
    }, 60000); // Checa a cada 1 minuto

    const http = require('http');

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

    // Escuta novas mensagens
    sock.ev.on('messages.upsert', async m => {
        const msg = m.messages[0];

        // Ignora se a mensagem for sua própria ou não contiver texto
        if (!msg.message || msg.key.fromMe) return;

        const remoteJid = msg.key.remoteJid;

        // Ignora grupos
        if (remoteJid.includes('@g.us')) return;

        const textMessage = msg.message.conversation || msg.message.extendedTextMessage?.text;

        if (textMessage) {
            const now = Date.now();
            let userData = userStates.get(remoteJid) || { state: 'START', lastActivity: 0, lastMessageTime: 0 };

            // ANTI-SPAM: Ignora se a mensagem veio muito rápido (menos de 1.5 segundos)
            if (now - userData.lastMessageTime < 1500) {
                console.log(`[ANTI-SPAM] Ignorando mensagem de ${remoteJid} por excesso de velocidade.`);
                return;
            }
            userData.lastMessageTime = now;

            // PROTEÇÃO DE TAMANHO: Ignora mensagens gigantescas
            if (textMessage.length > 500) {
                await sock.sendMessage(remoteJid, { text: "Ops! Sua mensagem é muito longa. Por favor, tente algo mais curto! ✨" });
                return;
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

            // Se expirou o tempo do menu, recomeça
            if (!userData.state || (now - userData.lastActivity > MENU_TIMEOUT_MS && userData.state !== 'HUMAN')) {
                userData.state = 'START';
                userData.lastActivity = now;
            }

            // Controle do atendimento humano
            if (userData.state === 'HUMAN') {
                if (textStr === '0') {
                    userData.state = 'START';
                    welcomeSent.delete(remoteJid);
                } else if (now - userData.lastActivity > HUMAN_TIMEOUT_MS) {
                    userData.state = 'START';
                } else {
                    userData.lastActivity = now;
                    userStates.set(remoteJid, userData);
                    return;
                }
            }

            userData.lastActivity = now;
            userStates.set(remoteJid, userData);

            // Mostra "digitando..."
            await sock.sendPresenceUpdate('composing', remoteJid);
            await new Promise(r => setTimeout(r, 1000));

            try {
                // BLOCO GLOBAL: Se o número for 1-8, forçamos o estado MENU
                // EXCEÇÕES: 
                // 1. Tela de avaliação (AWAITING_REVIEW): 1-5 são notas.
                // 2. Tela de ID de Pedido (AWAITING_ORDER_ID): Pode ser um ID curto.
                if (/^[1-8]$/.test(textStr)) {
                    if (userData.state === 'AWAITING_REVIEW' && /^[1-5]$/.test(textStr)) {
                        // Mantém em AWAITING_REVIEW
                    } else if (userData.state === 'AWAITING_ORDER_ID') {
                        // Mantém em AWAITING_ORDER_ID para processar o número do pedido
                    } else {
                        userData.state = 'MENU';
                    }
                }

                if (userData.state === 'START') {
                    const apiInfo = await fetchApi('/sistema/api/bot/info/');
                    const lastWelcome = welcomeSent.get(remoteJid) || 0;
                    const isRecent = (now - lastWelcome < 10 * 60 * 1000);

                    if (isRecent) {
                        await sock.sendMessage(remoteJid, { text: `Como posso te ajudar agora? ✨\n\n${menuOpcoes}` });
                    } else {
                        welcomeSent.set(remoteJid, now);
                        let statusText = apiInfo.is_open
                            ? `🟢 *Estamos ABERTOS!*\n${apiInfo.details || ""}`
                            : `🔴 *Estamos FECHADOS no momento.*\n${apiInfo.notice || ""}`;

                        const msgMenu = `Olá! Aqui é o atendimento virtual da *YasMimos*! 🧁✨\n\n` +
                            `${statusText.trim()}\n\n` +
                            `Como posso te ajudar hoje? Digite o *número* da opção desejada:\n\n${menuOpcoes}`;

                        await sock.sendMessage(remoteJid, { text: msgMenu });
                    }
                    userData.state = 'MENU';
                    userStates.set(remoteJid, userData);
                    return;
                }
                else if (userData.state === 'AWAITING_FIDELITY_ID') {
                    if (textStr === '0') {
                        userData.state = 'MENU';
                        await sock.sendMessage(remoteJid, { text: `Voltando ao menu principal... ✨\n\n${menuOpcoes}` });
                        userStates.set(remoteJid, userData);
                        return;
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

                                await sock.sendMessage(remoteJid, { text: msgFid });
                                userData.state = 'AWAITING_FIDELITY_ID';
                                userStates.set(remoteJid, userData);
                                return;
                            } else {
                                await sock.sendMessage(remoteJid, { text: "❌ Não encontrei nenhum cartão com esse ID. Verifique se digitou corretamente e *tente novamente*, ou digite *0* para voltar ao menu principal. ✨" });
                                return;
                            }
                        } catch (e) {
                            await sock.sendMessage(remoteJid, { text: "Houve um erro ao consultar o cartão. Tente novamente mais tarde." });
                            return;
                        }
                    }
                }
                else if (userData.state === 'AWAITING_FAQ') {
                    const choice = textStr.toUpperCase();
                    if (choice === '0') {
                        userData.state = 'MENU';
                        await sock.sendMessage(remoteJid, { text: `Voltando ao menu principal... ✨\n\n${menuOpcoes}` });
                        userStates.set(remoteJid, userData);
                        return;
                    } else if (choice === 'A') {
                        await sock.sendMessage(remoteJid, { text: "💳 *Formas de Pagamento:*\n\nAceitamos PIX (direto no site), Cartão de Crédito/Débito (via link ou na retirada) e Dinheiro.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes });
                        userData.state = 'MENU';
                    } else if (choice === 'B') {
                        await sock.sendMessage(remoteJid, { text: "🎨 *Personalização:*\n\nApenas a *Caixinha da Felicidade Personalizada* permite a escolha de sabores. Você escolhe os 4 brigadeiros diretamente no nosso site!\n\n⏳ *Tempo de Preparo:* Por ser uma encomenda artesanal, seu pedido será preparado em alguns dias após a confirmação. O tempo exato depende dos dias em que estivermos abertos (confira sempre o status no topo da conversa!). ✨\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes });
                        userData.state = 'MENU';
                    } else if (choice === 'C') {
                        await sock.sendMessage(remoteJid, { text: "🛵 *Entrega e Retirada:*\n\nAtualmente focamos em retiradas no Centro de Biociências (CB). Para entregas em outros locais, consulte a disponibilidade com um atendente.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n" + menuOpcoes });
                        userData.state = 'MENU';
                    } else {
                        await sock.sendMessage(remoteJid, { text: "Ops! Escolha A, B ou C, ou digite 0 para voltar ao menu principal." });
                        return;
                    }
                }
                else if (userData.state === 'AWAITING_REVIEW') {
                    await sock.sendMessage(remoteJid, { text: "Recebemos sua avaliação! Muito obrigado pelo feedback, ele nos ajuda a melhorar sempre. 🥰\n\nTenha um mimoso dia! ✨" });
                    userData.state = 'START';
                    welcomeSent.delete(remoteJid);
                    userStates.set(remoteJid, userData);
                    return;
                }
                else if (userData.state === 'AWAITING_ORDER_ID') {
                    const orderIdStr = textStr.replace(/\D/g, '');
                    if (orderIdStr === '0' || orderIdStr === '') {
                        userData.state = 'MENU';
                        await sock.sendMessage(remoteJid, { text: `Voltando ao menu principal... ✨\n\n${menuOpcoes}` });
                        userStates.set(remoteJid, userData);
                        return;
                    }
                    const orderId = parseInt(orderIdStr, 10);
                    try {
                        const orderInfo = await fetchApi(`/sistema/api/bot/order/${orderId}/`);
                        if (orderInfo.status === 'success') {
                            const captionText = `📦 *Status do Pedido #${orderInfo.order_id}*\n\n` +
                                `Status atual: *${orderInfo.status_display}*\n` +
                                `Valor Total: R$ ${orderInfo.total.toFixed(2).replace('.', ',')}\n\n` +
                                `*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada):\n\n${menuOpcoes}`;
                                
                            try {
                                await sock.sendMessage(remoteJid, {
                                    image: { url: `https://www.yasmimos.com.br/pedidos/receipt-image/${orderInfo.order_id}/` },
                                    caption: captionText
                                });
                            } catch (imgErr) {
                                console.error("Erro ao enviar imagem do comprovante:", imgErr);
                                await sock.sendMessage(remoteJid, { text: captionText });
                            }
                            userData.state = 'MENU';
                            userStates.set(remoteJid, userData);
                            return;
                        } else {
                            await sock.sendMessage(remoteJid, { text: `❌ Não consegui encontrar o pedido #${orderId}. Verifique se o número está correto.\n(Digite 0 para voltar ao menu)` });
                            return;
                        }
                    } catch (e) {
                        await sock.sendMessage(remoteJid, { text: `❌ Houve um erro ao buscar o pedido #${orderId}.\n(Digite 0 para voltar ao menu)` });
                        return;
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
                        await sock.sendMessage(remoteJid, { text: msgResposta });
                    }
                    else if (textStr === '2') {
                        await sock.sendMessage(remoteJid, { text: "Por favor, digite apenas o *número do seu pedido* (ex: 123) ou *0* para voltar ao menu:" });
                        userData.state = 'AWAITING_ORDER_ID';
                    }
                    else if (textStr === '3') {
                        await sock.sendMessage(remoteJid, { text: "Buscando nosso cardápio completo... ⏳🧁" });
                        try {
                            const prodData = await fetchApi(`/sistema/api/bot/products/all/`);
                            if (prodData.products && prodData.products.length > 0) {
                                for (let p of prodData.products) {
                                    const caption = `🍫 *${p.name}*\n💰 R$ ${p.price.toFixed(2).replace('.', ',')}\n📦 Estoque: ${p.stock} unidades\n\n👉 *Ver no site:* ${p.url}`;
                                    if (p.image_url) {
                                        await sock.sendMessage(remoteJid, { image: { url: p.image_url }, caption: caption });
                                    } else {
                                        await sock.sendMessage(remoteJid, { text: caption });
                                    }
                                    await new Promise(r => setTimeout(r, 800));
                                }
                                await sock.sendMessage(remoteJid, { text: `Acima estão os nossos mimos disponíveis! ✨\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}` });
                            } else {
                                await sock.sendMessage(remoteJid, { text: `No momento não temos produtos disponíveis no catálogo online.\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}` });
                            }
                        } catch (e) {
                            await sock.sendMessage(remoteJid, { text: "Houve um erro ao carregar o catálogo. Tente novamente mais tarde." });
                        }
                    }
                    else if (textStr === '4') {
                        const apiInfo = await fetchApi('/sistema/api/bot/info/');
                        let msgResposta = `*📍 Informações de Retirada/Entrega:*\n\n${apiInfo.notice || 'Sem avisos no momento.'}\n`;
                        if (apiInfo.details) {
                            msgResposta += `\n*Detalhes:*\n${apiInfo.details}`;
                        }
                        msgResposta += `\n\n*Posso te ajudar com algo mais?* ✨ (Digite o número da opção desejada)\n\n${menuOpcoes}`;
                        await sock.sendMessage(remoteJid, { text: msgResposta });
                    }
                    else if (textStr === '5') {
                        const faqMsg = `❓ *Dúvidas Frequentes:*\n\n` +
                            `*A* - Quais as formas de pagamento?\n` +
                            `*B* - Como personalizar meu pedido?\n` +
                            `*C* - Como funciona a retirada?\n\n` +
                            `*0* - Voltar ao menu principal`;
                        await sock.sendMessage(remoteJid, { text: faqMsg });
                        userData.state = 'AWAITING_FAQ';
                    }
                    else if (textStr === '6') {
                        await sock.sendMessage(remoteJid, { text: "🧁 *Cartão Fidelidade YasMimos*\n\nA cada *Caixinha da Felicidade* você ganha 1 selo! (Independente de ser personalizada ou não). 🎁\n\nAo completar *7 selos*, você ganha uma recompensa deliciosa!\n\nPara consultar seus pontos, por favor, digite o *ID do seu cartão* (Ex: Tassia) ou digite *0* para voltar ao menu:" });
                        userData.state = 'AWAITING_FIDELITY_ID';
                    }
                    else if (textStr === '7') {
                        await sock.sendMessage(remoteJid, { text: "Certo! O seu atendimento foi transferido para um humano. 👩‍💼\n\nNossa equipe te responderá o mais rápido possível por aqui mesmo.\n\n_(Para encerrar o atendimento humano e voltar pro menu automático, digite *0*)_" });
                        userData.state = 'HUMAN';
                    }
                    else if (textStr === '8') {
                        await sock.sendMessage(remoteJid, { text: "Obrigado por entrar em contato com a *YasMimos*! 🧁✨\n\nAntes de ir, como você avalia nosso atendimento hoje?\n\n*5* - Excelente ⭐\n*4* - Muito Bom\n*3* - Bom\n*2* - Regular\n*1* - Ruim" });
                        userData.state = 'AWAITING_REVIEW';
                    }
                    else {
                        // Não entendeu nada
                        await sock.sendMessage(remoteJid, { text: `Ops! Não entendi essa opção... 🤔\n\nPor favor, escolha uma das opções abaixo (1 a 8):\n\n${menuOpcoes}` });
                    }
                }

                userStates.set(remoteJid, userData);

            } catch (err) {
                console.error("Erro na integração com a API: ", err);
            }
        }
    });
}

connectToWhatsApp();
