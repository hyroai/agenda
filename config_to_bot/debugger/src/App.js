import Editor, { useMonaco } from "@monaco-editor/react";
import {
  KBarAnimator,
  KBarPortal,
  KBarPositioner,
  KBarProvider,
  KBarResults,
  KBarSearch,
  useKBar,
  useMatches,
  useRegisterActions,
} from "kbar";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import useWebSocket, { ReadyState } from "react-use-websocket";

import React from "react";
import tinykeys from "tinykeys";

// const monacoReddish = "#ce9178";
// const monacoWhiteish = "#d4d4d4";
const monacoGreenish = "#3dc9b0";
const monacoBlueish = "#569cd6";

const botTextColor = "white";
const errorTextColor = "white";
const humanTextColor = "yellowgreen";

const rowSpacing = { display: "flex", flexDirection: "column", gap: 10 };
const fieldNameColor = monacoGreenish;
const fieldValueColor = monacoBlueish;

const ServerError = ({ message }) => (
  <div
    style={{
      flexDirection: "row",
      justifyContent: "flex-start",
      gap: 20,
      display: "flex",
      color: errorTextColor,
    }}
  >
    <div>❗ {message}</div>
  </div>
);

const DebugSubgraph = ([key, { state, utter, participated }], i) => (
  <div key={i}>
    <span style={{ color: fieldNameColor }}>{key}</span>&nbsp;
    <span style={{ color: fieldValueColor }}>
      {state === null
        ? "?"
        : state === true
        ? "yes"
        : state === false
        ? "no"
        : Array.isArray(state)
        ? state.join(", ")
        : state}
    </span>
    <div style={{ color: botTextColor, fontSize: "8px" }}>
      {utter} {participated && "✔"}
    </div>
  </div>
);

const SubgraphsDebugger = (state) =>
  Object.keys(state).length && (
    <div>{Object.entries(state).map(DebugSubgraph)}</div>
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
    {state && SubgraphsDebugger(state)}
  </div>
);

const UserUtterance = ({ utterance }) => (
  <span style={{ color: humanTextColor }}>👩 {utterance}</span>
);
const Event = (event, i) => (
  <span key={i}>
    <>
      {event.type === "botUtterance" ? BotUtterance(event) : null}
      {event.type === "error" ? ServerError(event) : null}
      {event.type === "userUtterance" ? UserUtterance(event) : null}
    </>
  </span>
);

const userUtteranceEvent = (utterance) => ({
  type: "userUtterance",
  utterance,
});

const configurationType = "configuration";
const resetType = "reset";

const connectionStatus = {
  [ReadyState.CONNECTING]: { text: "Connecting ...", color: "yellow" },
  [ReadyState.OPEN]: { text: "Connected", color: "yellowgreen" },
  [ReadyState.CLOSING]: { text: "Disconnecting ...", color: "yellow" },
  [ReadyState.CLOSED]: { text: "Disconnected", color: "red" },
  [ReadyState.UNINSTANTIATED]: { text: "Uninstantiated", color: "red" },
};

const ConfigEditor = ({ text, setText }) => {
  const editorRef = useRef(null);
  useRegisterActions(
    [
      {
        name: "focus editor",
        shortcut: ["e"],
        keywords: "editor",
        perform: () => setTimeout(() => editorRef.current.focus(), 10),
      },
    ],
    [editorRef]
  );
  const monaco = useMonaco();
  const { query } = useKBar();
  const [dirty, setDirty] = useState(0);
  useEffect(() => {
    if (editorRef.current && monaco && query) {
      editorRef.current.addCommand(
        monaco.KeyMod.CtrlCmd | monaco.KeyCode.KEY_K,
        () => {
          query.toggle();
        }
      );
    }
  }, [editorRef, monaco, query, dirty]);

  return (
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
        onMount={(editor) => {
          setDirty(dirty + 1);
          editorRef.current = editor;
        }}
      />
    </div>
  );
};

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
  useRegisterActions(
    [
      {
        id: "focus chat",
        name: "focus chat",
        shortcut: ["c"],
        keywords: "chat",
        perform: () => setTimeout(() => ref.current.focus(), 10),
      },
    ],
    [ref]
  );
  return (
    <div
      style={{
        display: "flex",
        flexGrow: 1,
        ...rowSpacing,
        overflowY: "auto",
        backgroundColor: "#1e1e1e",
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

const StatusBar = ({ connectionStatus: { color, text } }) => (
  <div
    style={{
      display: "flex",
      gap: 10,
      flexDirection: "row",
      backgroundColor: "#1e1e1e",
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
    <div>Hit ctrl+k for commands</div>
  </div>
);

const App = ({ serverSocketUrl }) => {
  const [events, addEvent] = useReducer(
    (state, current) =>
      [configurationType, resetType].includes(current.type)
        ? []
        : [...state, current],
    []
  );
  const { sendJsonMessage, lastJsonMessage, readyState } = useWebSocket(
    serverSocketUrl || "ws://0.0.0.0:9000/converse",
    {
      shouldReconnect: () => didUnmount.current === false,
      reconnectAttempts: 100,
      reconnectInterval: 3000,
    }
  );

  const addEventSendingMessage = useCallback(
    (e) => {
      addEvent(e);
      sendJsonMessage(e);
    },
    [addEvent, sendJsonMessage]
  );

  const didUnmount = useRef(false);
  useEffect(() => () => (didUnmount.current = true), []);
  useEffect(() => {
    if (lastJsonMessage !== null) {
      addEvent(lastJsonMessage);
    }
  }, [lastJsonMessage, addEvent]);

  useEffect(() => {
    if (readyState === ReadyState.CONNECTING) addEvent({ type: "reset" });
  }, [readyState, addEvent]);
  const configExample =
    "slots:\n  - &name\n    ack: Nice to meet you {}!\n    ask: What is your name?\n    type: name\nactions:\n  - say: This is just an example for a configuration.\n    when: *name\nknowledge:\n  - faq:\n    - question: What is agenda?\n      answer: Agenda is a library to build bots with configurations.\ndebug:\n  - key: name\n    value: *name";
  const [configurationText, setConfigurationText] = useState(configExample);
  useEffect(() => {
    if (readyState === ReadyState.CONNECTING)
      addEventSendingMessage({
        type: configurationType,
        data: configurationText,
      });
  }, [readyState, addEventSendingMessage]);
  const [showEditor, setShowEditor] = useState(true);
  const { query } = useKBar();
  useEffect(() => {
    if (!query) return;
    const unsubscribe = tinykeys(window, {
      "$mod+p": (e) => {
        query.toggle();
        e.preventDefault();
        e.stopPropagation();
      },
    });
    return () => {
      unsubscribe();
    };
  }, [query]);

  useRegisterActions(
    [
      {
        id: "editor",
        name: "show/hide editor",
        shortcut: ["e"],
        keywords: "editor",
        perform: () => setShowEditor(!showEditor),
      },
      {
        id: "reload",
        name: "reload configuration",
        shortcut: ["r", "l"],
        keywords: "reload",
        perform: () =>
          addEventSendingMessage({
            type: configurationType,
            data: configurationText,
          }),
      },
      {
        id: "reset",
        name: "reset bot",
        shortcut: ["r", "s"],
        keywords: "reset",
        perform: () =>
          addEventSendingMessage({
            type: "reset",
          }),
      },
    ],
    [
      showEditor,
      setShowEditor,
      addEventSendingMessage,
      configurationText,
      configurationType,
    ]
  );
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
            addEventSendingMessage(userUtteranceEvent(text));
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
      <StatusBar connectionStatus={connectionStatus[readyState]} />
    </div>
  );
};

const RenderResults = () => {
  const { results } = useMatches();
  return (
    <KBarResults
      items={results}
      onRender={({ item, active }) =>
        typeof item === "string" ? (
          <div>{item}</div>
        ) : (
          <div
            style={{
              background: active ? "black" : "gray",
            }}
          >
            {item.name}
          </div>
        )
      }
    />
  );
};

const AppWithKbar = ({ serverSocketUrl, actions }) => (
  <KBarProvider actions={actions}>
    <KBarPortal>
      <KBarPositioner>
        <KBarAnimator>
          <KBarSearch />
          <RenderResults />
        </KBarAnimator>
      </KBarPositioner>
    </KBarPortal>
    <App serverSocketUrl={serverSocketUrl} />
  </KBarProvider>
);

export default AppWithKbar;
