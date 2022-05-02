import React, { useState, StrictMode } from "react";
import { createRoot } from "react-dom/client";
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

const rootElement = document.getElementById("root");
const root = createRoot(rootElement);

root.render(
  <StrictMode>
    <IdeWrapper />
  </StrictMode>
);
