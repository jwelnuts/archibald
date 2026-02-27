const STIMULUS_MODULE_URL = "https://unpkg.com/@hotwired/stimulus@3.2.2/dist/stimulus.js";

let stimulusModulePromise = null;
let stimulusApp = null;

const pendingRegistrations = [];
const registeredIdentifiers = new Set();

const loadStimulusModule = () => {
  if (!stimulusModulePromise) {
    stimulusModulePromise = import(STIMULUS_MODULE_URL);
  }
  return stimulusModulePromise;
};

const flushRegistrations = () => {
  if (!stimulusApp) {
    return;
  }

  while (pendingRegistrations.length > 0) {
    const [identifier, controllerClass] = pendingRegistrations.shift();
    if (!identifier || !controllerClass || registeredIdentifiers.has(identifier)) {
      continue;
    }
    stimulusApp.register(identifier, controllerClass);
    registeredIdentifiers.add(identifier);
  }
};

export const withStimulusModule = (callback) => loadStimulusModule().then(callback);

export const registerStimulusController = (identifier, controllerClass) => {
  pendingRegistrations.push([identifier, controllerClass]);
  flushRegistrations();
};

export const startStimulus = async () => {
  if (stimulusApp) {
    return stimulusApp;
  }

  try {
    const { Application } = await loadStimulusModule();
    stimulusApp = Application.start();
    window.MIOStimulus = stimulusApp;
    flushRegistrations();
    return stimulusApp;
  } catch (error) {
    console.error("Stimulus non disponibile:", error);
    throw error;
  }
};
