import { useEffect, useReducer, useRef, useState } from "react";
import useWebSocket, { ReadyState } from "react-use-websocket";

import Editor from "@monaco-editor/react";
import React from "react";

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

const configurationType = "configuration";
const resetType = "reset";

const event = (configurationText, textInput) =>
  textInput === resetType
    ? { type: textInput }
    : textInput === "reload"
    ? {
        type: configurationType,
        data: configurationText,
      }
    : userUtteranceEvent(textInput);

const connectionStatus = {
  [ReadyState.CONNECTING]: { text: "Connecting ...", color: "yellow" },
  [ReadyState.OPEN]: { text: "Connected", color: "yellowgreen" },
  [ReadyState.CLOSING]: { text: "Disconnecting ...", color: "yellow" },
  [ReadyState.CLOSED]: { text: "Disconnected", color: "red" },
  [ReadyState.UNINSTANTIATED]: { text: "Uninstantiated", color: "red" },
};

const ConfigEditor = ({ text, setText }) => (
  <div
    style={{
      display: "flex",
      flexBasis: "50%",
    }}
  >
    <Editor
      value={text}
      onChange={setText}
      theme="vs-dark"
      language="yaml"
      automaticLayout={true}
    />
  </div>
);

const Chat = ({ events, submit }) => {
  const [textInput, setTextInput] = useState("");
  const ref = useRef(null);
  useEffect(() => {
    ref.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "start",
    });
  }, [events]);
  return (
    <div
      style={{
        display: "flex",
        flexGrow: 1,
        ...rowSpacing,
        overflowY: "auto",
        backgroundColor: "#300a24",
      }}
    >
      <div style={rowSpacing}>{events.map(Event)}</div>
      <div style={{ color: humanTextColor, display: "flex" }}>
        <div>{">"}&nbsp;</div>
        <input
          ref={ref}
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
          onKeyDown={({ key }) => {
            if (key === "Enter") {
              submit(textInput);
              setTextInput("");
            }
          }}
          onChange={(e) => setTextInput(e.target.value)}
        />
      </div>
    </div>
  );
};

const StatusBar = ({
  showEditor,
  toggleEditor,
  connectionStatus: { color, text },
}) => (
  <div
    style={{
      backgroundColor: "#202124",
      display: "flex",
      gap: 10,
      flexDirection: "row",
    }}
  >
    <div
      style={{
        display: "flex",
        color,
      }}
    >
      {text}
    </div>
    <div onClick={toggleEditor}>{showEditor ? "close" : "open"} editor</div>
  </div>
);

const App = () => {
  const didUnmount = useRef(false);
  const [events, addEvent] = useReducer(
    (state, current) =>
      [configurationType, resetType].includes(current.type)
        ? []
        : [...state, current],
    []
  );
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
    if (lastJsonMessage !== null) {
      addEvent(lastJsonMessage);
    }
  }, [lastJsonMessage, addEvent]);

  useEffect(() => {
    if (readyState === ReadyState.CONNECTING) addEvent({ type: "reset" });
  }, [readyState, addEvent]);

  const [showEditor, setShowEditor] = useState(false);

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          overflow: "hidden",
          flexBasis: "100%",
        }}
      >
        <Chat
          submit={(text) => {
            if (readyState !== ReadyState.OPEN) {
              alert("not connected");
              return;
            }
            const e = event(configurationText, text);
            addEvent(e);
            sendJsonMessage(e);
          }}
          events={events}
        />
        {showEditor && (
          <ConfigEditor
            text={configurationText}
            setText={setConfigurationText}
          />
        )}
      </div>
      <StatusBar
        showEditor={showEditor}
        toggleEditor={() => setShowEditor(!showEditor)}
        connectionStatus={connectionStatus[readyState]}
      />
    </div>
  );
};

export default App;
