require("dotenv").config();

const TelegramBot = require("node-telegram-bot-api");
const { GoogleGenerativeAI } = require("@google/generative-ai");

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN, {
    polling: true
});

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

// 🧠 Memory
const memory = {};

// 📊 Your channel data
const channelData = `
Channel: @jv_60fps

Products:
- 4K 120FPS video upscaling
- TikTok & YouTube downloader
- Video enhancement tools

Common Issues:
- Download not working → Check internet or update app
- App not installing → Enable unknown sources
- Lag → Use lower resolution

Support:
Telegram: @jv_60fps
`;

bot.on("message", async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;

    if (!text) return;

    try {
        if (!memory[chatId]) memory[chatId] = [];

        memory[chatId].push(`User: ${text}`);
        memory[chatId] = memory[chatId].slice(-10);

        const prompt = `
You are an AI support bot for Telegram channel @jv_60fps.

Use this info:
${channelData}

Conversation:
${memory[chatId].join("\n")}

Reply helpfully and short:
`;

        const result = await model.generateContent(prompt);
        const reply = result.response.text();

        memory[chatId].push(`Bot: ${reply}`);

        bot.sendMessage(chatId, "🤖 " + reply);

    } catch (err) {
        bot.sendMessage(chatId, "❌ Error: " + err.message);
    }
});
