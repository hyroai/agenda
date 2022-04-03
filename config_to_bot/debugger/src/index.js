import React, { useState } from "react";
import ReactDOM from "react-dom";
import App from "./App";

const IdeWrapper = () => {
  const [configurationText, setConfigurationText] = useState();
  return (
    <App
      setConfigurationText={setConfigurationText}
      configurationText={configurationText}
    />
  );
};

ReactDOM.render(
  <React.StrictMode>
    <IdeWrapper />
  </React.StrictMode>,
  document.getElementById("root")
);
