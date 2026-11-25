async function createProgram({ stdout }) {
  let network = "allowed";
  try {
    await fetch("http://127.0.0.1:18765/examples/hello.b");
  } catch {
    network = "blocked";
  }
  const result = `storage=${typeof localStorage}; network=${network}\n`;
  for (const byte of new TextEncoder().encode(result)) stdout(byte);
}
