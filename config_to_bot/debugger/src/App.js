import { useEffect, useReducer, useRef, useState } from "react";
import useWebSocket, { ReadyState } from "react-use-websocket";

const rowSpacing = { display: "flex", flexDirection: "column", gap: 10 };

const renderDebugState = ([key, value], i) => (
  <div key={i} marginRight={1}>
    <span>{key}: </span>
    <span style={{ color: "red" }}>
      {JSON.stringify(value).replace("null", "?")}
    </span>
  </div>
);

const renderDebugStates = (state) =>
  state && Object.keys(state).length !== 0 ? (
    <div>{Object.entries(state).map(renderDebugState)}</div>
  ) : null;

const textToBotUtterance = ({ botUtterance, state }) => (
  <div
    style={{
      flexDirection: "row",
      justifyContent: "flex-start",
      gap: 20,
      display: "flex",
    }}
  >
    <div style={{ color: "white" }}>🤖 {botUtterance}</div>
    {renderDebugStates(state)}
  </div>
);
const textToUsertUtterance = ({ userUtterance }) => (
  <span style={{ color: "lightblue" }}>👩 {userUtterance}</span>
);
const renderEvent = (event, i) => (
  <span marginTop={1} key={i}>
    {event.userUtterance
      ? textToUsertUtterance(event)
      : event.botUtterance
      ? textToBotUtterance(event)
      : null}
  </span>
);

const App = () => {
  const didUnmount = useRef(false);
  const [events, addEvent] = useReducer(
    (state, current) =>
      ["reset", "reload"].includes(current.userUtterance)
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
      addEvent({ userUtterance: "reset" });
  }, [readyState, addEvent]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: "Connecting ...",
    [ReadyState.OPEN]: "Connected",
    [ReadyState.CLOSING]: "Disconnecting ...",
    [ReadyState.CLOSED]: "Disconnected",
    [ReadyState.UNINSTANTIATED]: "Uninstantiated",
  }[readyState];
  return (
    <>
      <div style={rowSpacing}>
        <div>{connectionStatus}</div>
        {readyState === ReadyState.OPEN && (
          <div style={rowSpacing}>
            <div style={rowSpacing}>{events.map(renderEvent)}</div>
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
                    addEvent({ userUtterance: textInput });
                    sendJsonMessage(textInput);
                    setTextInput("");
                  }
                }}
                onChange={(e) => setTextInput(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default App;
