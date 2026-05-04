require("dotenv").config();

const TelegramBot = require("node-telegram-bot-api");
const { OpenAI } = require("openai");

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN, {
    polling: true
});

const openai = new OpenAI({
    apiKey: process.env.OPENAI_KEY
});

// 🧠 Memory
const memory = {};

// 📊 Your channel knowledge
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

        memory[chatId].push({ role: "user", content: text });
        memory[chatId] = memory[chatId].slice(-10);

        const response = await openai.chat.completions.create({
            model: "gpt-4o-mini",
            messages: [
                {
                    role: "system",
                    content: `You are an AI support bot for Telegram channel @jv_60fps.

Use this info:
${channelData}

- Answer product questions clearly
- Help fix issues
- Be friendly and short
- If not related, reply normally`
                },
                ...memory[chatId]
            ]
        });

        const reply = response.choices[0].message.content;

        memory[chatId].push({ role: "assistant", content: reply });

        bot.sendMessage(chatId, "🤖 " + reply);

    } catch (err) {
        bot.sendMessage(chatId, "❌ Error: " + err.message);
    }
});
