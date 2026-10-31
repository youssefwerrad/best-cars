import { createContext, useContext } from "react";

export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function getCookie(name) {
  const prefix = `${name}=`;
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

async function getCsrfToken() {
  let token = getCookie("csrftoken");
  if (!token) {
    const response = await fetch("/djangoapp/whoami", { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error(`Could not initialize CSRF protection (${response.status})`);
    }
    token = getCookie("csrftoken");
  }
  if (!token) {
    throw new Error("CSRF cookie was not set by the server");
  }
  return token;
}

export async function api(path, body) {
  const isFormData = body instanceof FormData;
  const method = body === undefined ? "GET" : "POST";
  const opts = body !== undefined
    ? {
      method,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        "X-CSRFToken": await getCsrfToken(),
      },
      body: isFormData ? body : JSON.stringify(body),
    }
    : {};
  try {
    const response = await fetch("/djangoapp/" + path, { credentials: "same-origin", ...opts });
    const data = await response.json();
    return { ...data, status: data.status ?? response.status };
  } catch (error) {
    console.error("API request failed:", error);
    return { status: 500, message: "Network error. Please try again." };
  }
}

export function readCompareList() {
  try {
    return JSON.parse(localStorage.getItem("best-cars-compare") || "[]");
  } catch (error) {
    console.error("Could not read saved comparison list:", error);
    return [];
  }
}

export function writeCompareList(dealers) {
  localStorage.setItem("best-cars-compare", JSON.stringify(dealers));
}
