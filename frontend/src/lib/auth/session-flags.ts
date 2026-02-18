import { GuardState } from "@/shared/contracts";

function setCookie(name: string, value: string) {
  document.cookie = `${name}=${value}; path=/; max-age=86400; samesite=lax`;
}

function setStorage(name: string, value: string) {
  try {
    window.localStorage.setItem(name, value);
  } catch {
    // Ignore storage failures (private mode, blocked storage, etc.).
  }
}

export function setGuardFlags(state: GuardState) {
  setStorage("phase7_A", state.A ? "1" : "0");
  setStorage("phase7_V", state.V ? "1" : "0");
  setStorage("phase7_S", state.S ? "1" : "0");
  setCookie("phase7_A", state.A ? "1" : "0");
  setCookie("phase7_V", state.V ? "1" : "0");
  setCookie("phase7_S", state.S ? "1" : "0");
}

function readCookie(name: string): string | null {
  const part = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`));
  return part ? part.slice(name.length + 1) : null;
}

function readStorage(name: string): string | null {
  try {
    return window.localStorage.getItem(name);
  } catch {
    return null;
  }
}

export function readGuardFlags(): GuardState {
  const fallback: GuardState = { A: false, V: false, S: false };
  if (typeof document === "undefined") return fallback;

  const rawA = readStorage("phase7_A") ?? readCookie("phase7_A");
  const rawV = readStorage("phase7_V") ?? readCookie("phase7_V");
  const rawS = readStorage("phase7_S") ?? readCookie("phase7_S");

  return {
    A: rawA === "1",
    V: rawV === "1",
    S: rawS === "1",
  };
}
