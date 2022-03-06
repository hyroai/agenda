import React from "react";
import { useEffect, useReducer, useRef, useState } from "react";
import useWebSocket, { ReadyState } from "react-use-websocket";

const configurationFileEvent = (parsedConfigurationFile) => ({
  type: "configurationFile",
  data: parsedConfigurationFile,
});

const rowSpacing = { display: "flex", flexDirection: "column", gap: 10 };
const botTextColor = "white";
const humanTextColor = "yellowgreen";
const configurationFieldColor = "forestgreen";

const ServerError = ({ message, trace }) => (
  <div>
    <div>{message}</div>
    {trace && <div style={{ whiteSpace: "break-spaces" }}>{trace}</div>}
  </div>
);
const debugSubgraph = ([key, { state, utter, participated }], i) => (
  <div key={i}>
    <span style={{ color: configurationFieldColor }}>{key}</span>&nbsp;
    <span style={{ color: humanTextColor }}>
      {state === null
        ? "?"
        : state === true
        ? "yes"
        : state === false
        ? "no"
        : state}
    </span>
    <div style={{ color: botTextColor, fontSize: "8px" }}>
      {utter} {participated && "✔"}
    </div>
  </div>
);

const subgraphsDebugger = (state) =>
  Object.keys(state).length && (
    <div>{Object.entries(state).map(debugSubgraph)}</div>
  );

const BotUtterance = ({ utterance, state }) => (
  <div
    style={{
      flexDirection: "row",
      justifyContent: "flex-start",
      gap: 20,
      display: "flex",
      color: botTextColor,
    }}
  >
    <div>🤖 {utterance}</div>
    {state && subgraphsDebugger(state)}
  </div>
);

const UserUtterance = ({ utterance }) => (
  <span style={{ color: humanTextColor }}>👩 {utterance}</span>
);
const Event = (event, i) => (
  <span key={i}>
    <>
      {event.type === "botUtterance" ? BotUtterance(event) : null}
      {event.type === "botError" ? ServerError(event) : null}
      {event.type === "userUtterance" ? UserUtterance(event) : null}
    </>
  </span>
);

const userUtteranceEvent = (textInput) => ({
  type: "userUtterance",
  utterance: textInput,
});

const event = (textInput) =>
  ["reset", "reload"].includes(textInput)
    ? { type: textInput }
    : userUtteranceEvent(textInput);

const connectionStatus = {
  [ReadyState.CONNECTING]: { text: "Connecting ...", color: "yellow" },
  [ReadyState.OPEN]: { text: "Connected", color: "yellowgreen" },
  [ReadyState.CLOSING]: { text: "Disconnecting ...", color: "yellow" },
  [ReadyState.CLOSED]: { text: "Disconnected", color: "red" },
  [ReadyState.UNINSTANTIATED]: { text: "Uninstantiated", color: "red" },
};

const App = () => {
  const didUnmount = useRef(false);
  const [events, addEvent] = useReducer(
    (state, current) =>
      ["reset", "reload"].includes(current.type) ? [] : [...state, current],
    []
  );
  const [textInput, setTextInput] = useState("");
  const [configurationText, setConfigurationText] = useState("");
  const { sendJsonMessage, lastJsonMessage, readyState } = useWebSocket(
    "ws://0.0.0.0:9000/converse",
    {
      shouldReconnect: () => didUnmount.current === false,
      reconnectAttempts: 100,
      reconnectInterval: 3000,
    }
  );
  useEffect(() => () => (didUnmount.current = true), []);
  useEffect(() => {
    inputRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);
  useEffect(() => {
    if (lastJsonMessage !== null) {
      addEvent(lastJsonMessage);
    }
  }, [lastJsonMessage, addEvent]);

  useEffect(() => {
    if (readyState === ReadyState.CONNECTING) addEvent({ type: "reset" });
  }, [readyState, addEvent]);

  const inputRef = useRef(null);

  return (
    <div style={{ display: "flex", flexDirection: "row", height: "100vh" }}>
      <div style={rowSpacing}>
        <div style={{ color: connectionStatus[readyState].color }}>
          {connectionStatus[readyState].text}
        </div>
        {readyState === ReadyState.OPEN && (
          <div style={rowSpacing}>
            <div style={rowSpacing}>{events.map(Event)}</div>
            <div
              ref={inputRef}
              style={{ color: humanTextColor, display: "flex" }}
            >
              <div>{">"}&nbsp;</div>
              <input
                style={{
                  outline: "none",
                  display: "flex",
                  flex: 1,
                  fontFamily: "monospace",
                  background: "transparent",
                  color: humanTextColor,
                  border: "none",
                }}
                autoFocus={true}
                type="text"
                value={textInput}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && readyState === ReadyState.OPEN) {
                    addEvent(event(textInput));
                    sendJsonMessage(event(textInput));
                    setTextInput("");
                  }
                }}
                onChange={(e) => setTextInput(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <textarea
          style={{
            background: "transparent",
            color: "white",
            border: "2px solid greenyellow",
            flex: 1,
          }}
          defaultValue={configurationText}
          onChange={(e) => setConfigurationText(e.target.value)}
        />
        <button
          disabled={readyState !== ReadyState.OPEN}
          onClick={() => {
            const configurationEvent =
              configurationFileEvent(configurationText);
            addEvent(configurationEvent);
            sendJsonMessage(configurationEvent);
          }}
        >
          Submit
        </button>
      </div>
    </div>
  );
};

export default App;
