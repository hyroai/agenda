import {useEffect, useReducer, useRef, useState} from "react";
import useWebSocket, {ReadyState} from "react-use-websocket";

const rowSpacing = { display: "flex", flexDirection: "column", gap: 10 };

const ServerError = ({message, trace}) =>
  (<div>
  <div>{message}</div>
    {trace && <div style={{whiteSpace: "break-spaces"}}>{trace}</div>}
  </div>)
const DebugState = ([key, value], i) => (
  <div key={i}>
    <span>{key}: </span>
    <span style={{ color: "red" }}>
      {JSON.stringify(value).replace("null", "?")}
    </span>
  </div>
);

const DebugStates = (state) =>(
  Object.keys(state).length !== 0 && (
    <div>{Object.entries(state).map(DebugState)}</div>
  ))

const BotUtterance = ({ utterance, state }) => (
  <div
    style={{
      flexDirection: "row",
      justifyContent: "flex-start",
      gap: 20,
      display: "flex",
    }}
  >
    <div style={{ color: "white" }}>🤖 {utterance}</div>
    {state && DebugStates(state)}
  </div>
);

const UserUtterance = ({ utterance }) => (
  <span style={{ color: "lightblue" }}>👩 {utterance}</span>
);
const Event = (event, i) => (
  <span key={i}>
    <>
    {event.type === "botUtterance" ? BotUtterance(event):null}
    {event.type === "botError" ? ServerError(event):null}
    {event.type === "userUtterance" ? UserUtterance(event):null}
  </>
  </span>
);

const userUtteranceEvent = (textInput) => ({type: "userUtterance", utterance: textInput})


function event(textInput) {
  return ["reset", "reload"].includes(textInput) ? {"type": textInput} : userUtteranceEvent(textInput);
}

const App = () => {
  const didUnmount = useRef(false);
  const [events, addEvent] = useReducer(
    (state, current) =>
      ["reset", "reload"].includes(current.type)
        ? []
        : [...state, current],
    []
  );
  const [textInput, setTextInput] = useState("");
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
    console.log(
      {
        [ReadyState.CONNECTING]: "Connecting",
        [ReadyState.OPEN]: "Open",
        [ReadyState.CLOSING]: "Closing",
        [ReadyState.CLOSED]: "Closed",
        [ReadyState.UNINSTANTIATED]: "Uninstantiated",
      }[readyState]
    );
    if (readyState === ReadyState.CONNECTING)
      addEvent({ type: "reset" });
  }, [readyState, addEvent]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: "Connecting ...",
    [ReadyState.OPEN]: "Connected",
    [ReadyState.CLOSING]: "Disconnecting ...",
    [ReadyState.CLOSED]: "Disconnected",
    [ReadyState.UNINSTANTIATED]: "Uninstantiated",
  }[readyState];
  return (
    <div style={rowSpacing}>
      <div>{connectionStatus}</div>
      {readyState === ReadyState.OPEN && (
        <div style={rowSpacing}>
          <div style={rowSpacing}>{events.map(Event)}</div>
          <div style={{ display: "flex" }}>
            <div>{">"}&nbsp;</div>
            <input
              style={{
                outline: "none",
                display: "flex",
                flex: 1,
                fontFamily: "monospace",
                background: "transparent",
                color: "white",
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
  );
};

export default App;
