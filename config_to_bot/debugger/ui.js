import { Box, Text, render } from "ink";
import React, { useEffect, useReducer, useState } from "react";

import TextInput from "ink-text-input";
import WebSocket from "ws";

const debugStatesToText = (keyValue, i) => (
  <Box key={i}>
    <Text color="red">
      {i != 0 ? "," : ""} {keyValue[0]} :{" "}
    </Text>
    <Text color="white">{JSON.stringify(keyValue[1])}</Text>
  </Box>
);

const textToBotUtterance = ({ botUtterance, state }) => (
  <Box>
    <Text color="white">🤖 {botUtterance}</Text>
    {state != null && Object.keys(state).length != 0 ? (
      <Box>
        <Text>[</Text>
        {Object.entries(state).map(debugStatesToText)}
        <Text>]</Text>
      </Box>
    ) : null}
  </Box>
);
const textToUsertUtterance = ({ userUtterance }) => (
  <Text color="green">👩 {userUtterance}</Text>
);

const FullScreen = ({ children }) => {
  const [size, setSize] = useState({
    columns: process.stdout.columns,
    rows: process.stdout.rows,
  });

  useEffect(() => {
    const onResize = () =>
      setSize({
        columns: process.stdout.columns,
        rows: process.stdout.rows,
      });

    process.stdout.on("resize", onResize);
    process.stdout.write("\x1b[?1049h");
    return () => {
      process.stdout.off("resize", onResize);
      process.stdout.write("\x1b[?1049l");
    };
  }, []);

  return (
    <Box width={size.columns} height={size.rows}>
      {children}
    </Box>
  );
};

const App = () => {
  const [events, addEvent] = useReducer(
    (state, current) =>
      ["reset", "reload"].includes(current.userUtterance)
        ? []
        : [...state, current],
    []
  );
  const [textInput, setTextInput] = useState("");
  const [socket, setSocket] = useState(null);
  useEffect(() => {
    if (socket == null) {
      const socket = new WebSocket(`${"ws://0.0.0.0:9000"}/converse`);
      setSocket(socket);
      socket.addEventListener("message", ({ data }) => {
        addEvent(JSON.parse(data));
      });
      return () => {
        socket.close();
        setSocket(null);
      };
    }
  }, [setSocket]);

  const renderEvent = (event, i) => (
    <Box marginTop={1} key={i}>
      {event.userUtterance
        ? textToUsertUtterance(event)
        : event.botUtterance
        ? textToBotUtterance(event)
        : null}
    </Box>
  );

  return (
    <FullScreen>
      <Box marginLeft={4} flexDirection="column">
        <Box flexDirection="column">{events.map(renderEvent)}</Box>
        <Box marginTop={2}>
          <TextInput
            value={textInput}
            onChange={setTextInput}
            onSubmit={() => {
              if (!socket) {
                return;
              }
              if (socket.readyState === WebSocket.OPEN) {
                addEvent({ userUtterance: textInput });
                socket.send(JSON.stringify(textInput));
                setTextInput("");
              }
            }}
          />
        </Box>
      </Box>
    </FullScreen>
  );
};

render(<App />);
