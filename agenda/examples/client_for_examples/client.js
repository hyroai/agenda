const WebSocket = require("ws");
const prompt = require("prompt-async");

// Create WebSocket connection.
const socket = new WebSocket(`${"ws://0.0.0.0:9000"}/converse`);

// Listen for messages
socket.addEventListener("message", function ({ data }) {
  eventData = JSON.parse(data);
  resultArray.push("Bot: " + eventData[0].replace(/(^"|"$)/g, ""));
  if (eventData.length > 1) {
    debugArray.push("States: " + eventData[1]);
  }
  render();
});

const resultArray = [];
const debugArray = [];

prompt.start();
const start = async () => {
  while (true) {
    const { userInput } = await prompt.get(["userInput"]);
    resultArray.push("User: " + userInput);
    render();
    await socket.send(JSON.stringify(userInput));
  }
};

const render = () => {
  console.clear();
  console.log(resultArray.join("\n"));
};
start();
