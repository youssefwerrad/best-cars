import { createContext, useContext } from "react";

export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export async function api(path, body) {
  const isFormData = body instanceof FormData;
  const opts = body
    ? {
      method: "POST",
      headers: isFormData ? {} : { "Content-Type": "application/json" },
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
