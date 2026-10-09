import { test, expect } from "@playwright/test";

for (const photo of ["../backend/assets/photos/00.jpg", "../backend/tests/fixtures/shirt.avif"]) {
test(`local photo recognition adds ${photo} without the attribute form`, async ({page}) => {
  test.skip(process.env.LOCAL_VISION_E2E !== "1", "Requires a server running the optional local model");
  const account = await page.request.post("/api/auth/register", {data:{email:`local-${Date.now()}@example.com`,password:"local-test-password"}});
  expect(account.ok()).toBeTruthy();
  await page.request.put("/api/profile", {data:{display_name:"Local photo test",outfit_style:"all",default_occasion:"everyday"}});
  await page.goto("/");
  await page.getByRole("button", {name:"My wardrobe"}).click();
  await page.getByRole("button", {name:"+ Add garment"}).click();
  await page.getByLabel("Choose a garment photo", {exact:false}).setInputFiles(photo);
  await expect(page.getByRole("heading", {name:"White shirt",exact:true})).toBeVisible({timeout:60000});
  await expect(page.getByRole("dialog", {name:"Review garment attributes"})).toHaveCount(0);
  await expect(page.getByRole("status").filter({hasText:"Photo added to your wardrobe"})).toBeVisible();
  await page.reload();
  await page.getByRole("button", {name:"My wardrobe"}).click();
  await expect(page.getByRole("heading", {name:"White shirt",exact:true})).toBeVisible();
  await page.screenshot({path:"../docs/screenshots/local-recognition.png",fullPage:true});
});

}
