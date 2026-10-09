import { test, expect } from "@playwright/test";
test("interview demo, one casual replacement, and feedback", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the demo wardrobe" }).click();
  await expect(
    page.getByRole("heading", { name: "What’s on your agenda?" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Find my outfits" }).click();
  await expect(page.getByTestId("outfit")).toHaveCount(3, { timeout: 30000 });
  const board = page.getByTestId("outfit").first();
  const before = await board
    .getByTestId("board-item")
    .evaluateAll((nodes) =>
      nodes.map((n) => n.getAttribute("data-garment-id")),
    );
  await board.getByRole("button", { name: "More casual", exact: true }).click();
  await expect(board.locator(".changed-label")).toBeVisible();
  const after = await board
    .getByTestId("board-item")
    .evaluateAll((nodes) =>
      nodes.map((n) => n.getAttribute("data-garment-id")),
    );
  expect(before.filter((id) => !after.includes(id))).toHaveLength(1);
  expect(after.filter((id) => !before.includes(id))).toHaveLength(1);
  await expect(board.locator(".substitution")).toContainText(
    "All other garment IDs",
  );
  await board.getByRole("button", { name: "♡ Liked", exact: true }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Liked recorded" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Your preferences" }).click();
  await expect(page.getByText("1 learning events")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/preferences.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Outfit planner" }).click();
  await page.screenshot({
    path: "../docs/screenshots/planner.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "My wardrobe" }).click();
  await expect(page.locator(".garment-card")).toHaveCount(32);
  await page.screenshot({
    path: "../docs/screenshots/wardrobe.png",
    fullPage: true,
  });
});
test("manual wardrobe entry and recoverable constraint conflict", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the demo wardrobe" }).click();
  await page.getByRole("button", { name: "My wardrobe" }).click();
  await page.getByRole("button", { name: "+ Add garment" }).click();
  await page.getByLabel("Garment name").fill("My blue shirt");
  await page.getByRole("button", { name: "Confirm attributes & save" }).click();
  await expect(
    page.getByRole("heading", { name: "My blue shirt" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Outfit planner" }).click();
  await page.getByText("Required & excluded pieces").click();
  await page.getByLabel("Require Laundry Oxford", { exact: true }).check();
  await page.getByRole("button", { name: "Find my outfits" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "required item" }),
  ).toBeVisible();
});

test("mobile layout and keyboard review dialog", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the demo wardrobe" }).click();
  await expect(
    page.getByRole("heading", { name: "What’s on your agenda?" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "My wardrobe" }).click();
  await page.getByRole("button", { name: "+ Add garment" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.getByRole("button", { name: "Confirm attributes & save" }).focus();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Close garment editor" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
});


test("signup profile is remembered after refresh and signing in again", async ({page}) => {
  const email = `profile-${Date.now()}@example.com`;
  await page.goto("/");
  await page.getByLabel("Email",{exact:true}).fill(email);
  await page.getByLabel("Password",{exact:true}).fill("test-password-123");
  await page.getByRole("button",{name:"Create account"}).click();
  await expect(page.getByRole("heading",{name:"Let’s make this yours"})).toBeVisible();
  await page.getByLabel("Your name",{exact:true}).fill("Alex");
  await page.getByLabel("Outfits for",{exact:true}).selectOption("men");
  await page.getByLabel("Usual occasion",{exact:true}).selectOption("weekend");
  await page.getByRole("button",{name:"Save my profile"}).click();
  await expect(page.getByRole("button",{name:/Outfits for: Men/})).toBeVisible();
  await expect(page.getByLabel("Occasion",{exact:true})).toHaveValue("weekend");
  await page.getByRole("button",{name:"Find my outfits"}).click();
  await expect(page.getByRole("heading",{name:"Add clothes to get started"})).toBeVisible();
  await expect(page.getByRole("alert").filter({hasText:"Your wardrobe is empty"})).toContainText("Your wardrobe is empty");
  await expect(page.getByTestId("outfit")).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("button",{name:/Outfits for: Men/})).toBeVisible();
  await page.getByRole("button",{name:"Sign out",exact:true}).click();
  await page.getByLabel("Email",{exact:true}).fill(email);
  await page.getByLabel("Password",{exact:true}).fill("test-password-123");
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("button",{name:/Outfits for: Men/})).toBeVisible();
  await expect(page.getByLabel("Occasion",{exact:true})).toHaveValue("weekend");
  await page.getByRole("button",{name:"Your profile"}).click();
  await expect(page.getByLabel("Your name",{exact:true})).toHaveValue("Alex");
  await expect(page.getByLabel("Outfits for",{exact:true})).toHaveValue("men");
  await page.screenshot({path:"../docs/screenshots/profile.png",fullPage:true});
});

