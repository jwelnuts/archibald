import * as StimulusModule from "@hotwired/stimulus";

let stimulusApp = null;

const pendingRegistrations = [];
const registeredIdentifiers = new Set();

const loadStimulusModule = () => Promise.resolve(StimulusModule);

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
  const { Application } = await loadStimulusModule();
  stimulusApp = Application.start();
  window.MIOStimulus = stimulusApp;
  flushRegistrations();
  return stimulusApp;
};
