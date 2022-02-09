import WebSocket from "ws";
import React, { useState, useEffect, useReducer } from "react";
import { render, Box, Text, Newline } from "ink";
import TextInput from "ink-text-input";

const textToBotUtterance = ({ botUtterance, state }) => (
	<Box>
		<Text color="blue">Bot: {botUtterance}</Text>
		{state ? <Text color="red">  {JSON.stringify(state)}</Text> : null}
	</Box>
);
const textToUsertUtterance = ({ userUtterance }) => (
	<Text color="green">User: {userUtterance}</Text>
);

const App = () => {
	const [events, addEvent] = useReducer(
		(state, current) => [...state, current],
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
	const renderEvent = (event, i) => {
		if (event.userUtterance) {
			return <Box key={i}>{textToUsertUtterance(event)}</Box>;
		}
		if (event.botUtterance) {
			return <Box key={i}>{textToBotUtterance(event)}</Box>;
		}
	};
	return (
		<Box flexDirection="column">
			<Box flexDirection="column">{events.map(renderEvent)}</Box>
			<Box>
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
	);
};

render(<App />);
