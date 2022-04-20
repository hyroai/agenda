const express = require("express");

const app = express();

app.post("/available-slots", ({}, res) => {
  res.json(["2022-04-30T17:20:00"]);
});

const port = process.env.PORT || 8000;

app.listen(port, () => console.log(`app listening at post ${port}`));
