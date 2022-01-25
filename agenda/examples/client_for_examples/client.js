const WebSocket = require("ws");
const prompt = require("prompt-async");

// Create WebSocket connection.
const socket = new WebSocket(`${"ws://0.0.0.0:9000"}/converse`);

// Listen for messages
socket.addEventListener("message", function (event) {
  someArray.push("Bot utterance: " + event.data);
  render()
});

const someArray = []

prompt.start();
const start = async () => {
  while (true) {
    const {userInput} = await prompt.get(["userInput"]);
    someArray.push("User utterance: " + userInput);
    render()
    await socket.send(JSON.stringify(userInput));
  }
};

const render = () => {
  console.clear()
  console.log(someArray.join('\n'))
}
start();
