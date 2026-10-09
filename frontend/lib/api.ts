import createClient from "openapi-fetch";
import type { paths, components } from "./api-schema";
export type Garment = components["schemas"]["GarmentView"];
export type Attributes = components["schemas"]["Attributes"];
export type Context = components["schemas"]["Context"];
export type Outfit = components["schemas"]["OutfitView"];
export type User = components["schemas"]["UserView"];
export type Insight = components["schemas"]["InsightsView"];
export type Event = components["schemas"]["FeedbackView"];
export type Analysis = components["schemas"]["AnalysisView"];
export const api = createClient<paths>({
  baseUrl: "/api",
  credentials: "same-origin",
});
export function unwrap<T>(response: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (!response.response.ok || response.data === undefined) {
    const err = response.error as
      | { detail?: { code?: string; message?: string } }
      | undefined;
    throw new Error(
      err?.detail?.message ||
        `Request failed (${response.response.status}). Please try again.`,
    );
  }
  return response.data;
}
export const defaultAttributes: Attributes = {
  name: "",
  category: "shirt",
  slot: "top",
  audience: "unisex",
  primary_color: "white",
  secondary_color: null,
  pattern: "solid",
  warmth: 1,
  formality: 2,
  seasons: ["spring", "autumn"],
  weather: ["dry"],
  tags: [],
  laundry: "clean",
  notes: "",
};
export const slots: Record<string, Attributes["slot"]> = {
  shirt: "top",
  knit: "top",
  trousers: "bottom",
  skirt: "bottom",
  jeans: "bottom",
  dress: "onepiece",
  jumpsuit: "onepiece",
  sneakers: "shoes",
  loafers: "shoes",
  dress_shoes: "shoes",
  boots: "shoes",
  coat: "outerwear",
  jacket: "outerwear",
  scarf: "accessory",
  bag: "accessory",
};
export const colors = [
  "black",
  "white",
  "navy",
  "gray",
  "beige",
  "brown",
  "blue",
  "green",
  "red",
  "pink",
  "purple",
  "yellow",
] as const;
