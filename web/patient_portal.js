export function onLogin(user) {
  console.log("login ok", user.id);
  console.log(user.email);
  console.log(user);
}

export function renderProfile(patient) {
  console.debug("profile", patient.mrn, patient.diagnosis);
}
