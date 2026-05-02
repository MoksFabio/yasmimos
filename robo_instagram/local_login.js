require('dotenv').config({ path: '../.env' });
const { IgApiClient } = require('instagram-private-api');
const fs = require('fs');

async function loginLocally() {
    const ig = new IgApiClient();
    const username = process.env.IG_USERNAME;
    const password = process.env.IG_PASSWORD;

    if (!username || !password) {
        console.error("❌ Configure IG_USERNAME e IG_PASSWORD no seu .env primeiro!");
        return;
    }

    ig.state.generateDevice(username);

    console.log(`Tentando logar com o seu IP Residencial na conta: ${username}...`);
    try {
        await ig.account.login(username, password);
        const state = await ig.state.serialize();
        delete state.constants; // Limpa coisas grandes desnecessárias
        fs.writeFileSync(__dirname + '/ig_state.json', JSON.stringify(state));
        console.log('✅ Login feito com sucesso! Arquivo "ig_state.json" criado.');
        console.log('Sua sessão foi salva com sucesso para ser enviada para a Square Cloud!');
    } catch (e) {
        console.error('❌ Falha ao logar localmente:', e.message);
    }
}

loginLocally();
