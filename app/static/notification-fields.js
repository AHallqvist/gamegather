"use strict";

document.querySelectorAll("form").forEach((form) => {
  const method = form.querySelector("[data-notification-method]");
  const target = form.querySelector("[data-notification-target]");
  if (!method || !target) return;
  const label = form.querySelector("[data-notification-label]");
  const instructions = form.querySelector("[data-notification-instructions]");
  const error = form.querySelector("[data-notification-error]");
  const smsPattern = /^\+467[02369][0-9]{7}$/;
  const smsError = "Enter a Swedish mobile number in +46 format, for example +46701234567.";

  function validate(showError) {
    const invalidSMS = method.value === "sms" && target.value !== "" && !smsPattern.test(target.value);
    target.setCustomValidity(invalidSMS ? smsError : "");
    const visible = showError && invalidSMS;
    error.textContent = visible ? smsError : "";
    error.hidden = !visible;
    target.setAttribute("aria-invalid", visible ? "true" : "false");
  }

  function update() {
    const option = method.selectedOptions[0];
    label.textContent = option.dataset.label;
    instructions.textContent = option.dataset.instructions;
    target.type = method.value === "email" ? "email" : method.value === "sms" ? "tel" : "text";
    target.placeholder = method.value === "sms" ? "+46701234567" : method.value === "email" ? "you@example.com" : option.dataset.label;
    const telegramLink = form.querySelector("[data-telegram-link]");
    if (telegramLink) telegramLink.hidden = method.value !== "telegram";
    target.autocomplete = method.value === "email" ? "email" : method.value === "sms" ? "tel" : "off";
    if (method.value === "sms") {
      target.pattern = "\\+467[02369][0-9]{7}";
      target.title = smsError;
    } else {
      target.removeAttribute("pattern");
      target.removeAttribute("title");
    }
    validate(true);
  }

  method.addEventListener("change", update);
  target.addEventListener("input", () => validate(true));
  target.addEventListener("blur", () => validate(true));
  target.addEventListener("invalid", () => validate(true));
  update();
});
