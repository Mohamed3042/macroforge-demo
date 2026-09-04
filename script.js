const demoButton = document.querySelector("#run-demo");
const demoStatus = document.querySelector("#demo-status");
const demoSteps = [...document.querySelectorAll("[data-demo-step]")];
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let activeRun = 0;

const sleep = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

async function runWalkthrough() {
  const runId = ++activeRun;
  const delay = reducedMotion.matches ? 1 : 430;
  const labels = ["recorded", "reviewed", "bound", "scoped", "completed"];

  demoButton.disabled = true;
  demoButton.querySelector(".play-icon").textContent = "■";
  demoStatus.dataset.complete = "false";
  demoStatus.textContent = "Following the local execution path…";

  demoSteps.forEach((step, index) => {
    step.dataset.state = "idle";
    step.querySelector(".trace-signal").textContent = index === 0 ? "ready" : "waiting";
  });

  for (let index = 0; index < demoSteps.length; index += 1) {
    if (runId !== activeRun) return;
    const step = demoSteps[index];
    step.dataset.state = "active";
    step.querySelector(".trace-signal").textContent = "running";
    await sleep(delay);
    step.dataset.state = "done";
    step.querySelector(".trace-signal").textContent = labels[index];
  }

  demoStatus.textContent = "Walkthrough complete — the measured path ends with one click and exact 68-character Notepad readback.";
  demoStatus.dataset.complete = "true";
  demoButton.disabled = false;
  demoButton.querySelector(".play-icon").textContent = "↻";
}

demoButton.addEventListener("click", runWalkthrough);
