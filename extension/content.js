/* PixelTrail content script: adds a "Track" chip to Gmail compose windows and
   inserts an invisible 1x1 tracking pixel into the draft body. */

function buildPixel(url) {
  const img = document.createElement("img");
  img.src = url;
  img.width = 1;
  img.height = 1;
  img.alt = "";
  img.setAttribute("data-pixeltrail", "1");
  img.setAttribute("style", "display:none;width:1px;height:1px;border:0");
  return img;
}

function activeBody() {
  const bodies = Array.from(document.querySelectorAll('div[aria-label][role="textbox"]'));
  return bodies.find((el) => el.offsetParent !== null) || bodies[0] || null;
}

function insertPixel(url, confirmSeenUrl) {
  const body = activeBody();

  if (!body) {
    return {
      ok: false,
      error: "Open a Gmail compose window first."
    };
  }

  // Remove any existing PixelTrail tracking elements
  body
    .querySelectorAll('[data-pixeltrail="1"]')
    .forEach((el) => el.remove());

  // Add invisible tracking pixel
  body.appendChild(buildPixel(url));

  // Add Confirm Seen link
  if (confirmSeenUrl) {
    const wrapper = document.createElement("div");
    wrapper.setAttribute("data-pixeltrail", "1");
    wrapper.style.marginTop = "12px";

    const link = document.createElement("a");
    link.href = confirmSeenUrl;
    link.textContent = "✓ Confirm you've seen this email";
    link.target = "_blank";
    link.rel = "noopener noreferrer";

    wrapper.appendChild(link);
    body.appendChild(wrapper);
  }

  return { ok: true };
}

function removePixel() {
  const body = activeBody();
  if (!body) return { ok: false, error: "Open a Gmail compose window first." };
  body.querySelectorAll('img[data-pixeltrail="1"]').forEach((el) => el.remove());
  return { ok: true };
}
function trackLinks(trackingId) {
  const body = activeBody();

  if (!body) {
    return {
      ok: false,
      error: "Open a Gmail compose window first."
    };
  }

  if (!trackingId) {
    return {
      ok: false,
      error: "Tracking ID is missing."
    };
  }

  const links = Array.from(body.querySelectorAll("a[href]"));

  let trackedCount = 0;

  links.forEach((link) => {
    const originalUrl = link.getAttribute("href");

    if (!originalUrl) return;

    let targetUrl = originalUrl;

    // If this is already a PixelTrail click link,
    // recover the original URL and use the NEW tracking ID.
    if (originalUrl.includes("/track/click/")) {
      const savedOriginal =
        link.getAttribute("data-pixeltrail-original-url");

      if (savedOriginal) {
        targetUrl = savedOriginal;
      } else {
        try {
          const parsed = new URL(originalUrl);
          const original = parsed.searchParams.get("url");

          if (original) {
            targetUrl = original;
          } else {
            return;
          }
        } catch {
          return;
        }
      }
    }

    // Never track the Confirm Seen link
    if (targetUrl.includes("/track/seen/")) {
      return;
    }

    // Only track normal web links
    if (
      !targetUrl.startsWith("http://") &&
      !targetUrl.startsWith("https://")
    ) {
      return;
    }

    const encodedUrl = encodeURIComponent(targetUrl);

    const trackingUrl =
    `https://pixeltrail.onrender.com/track/click/${trackingId}?url=${encodedUrl}`;

    link.setAttribute("href", trackingUrl);

    link.setAttribute(
      "data-pixeltrail-original-url",
      targetUrl
    );

    link.setAttribute(
      "data-pixeltrail-tracked",
      "true"
    );

    trackedCount++;
  });

  return {
    ok: true,
    trackedCount: trackedCount
  };
}

function addChips() {
  document.querySelectorAll("table.aoP, div.aDh, div.iN").forEach(() => {});
  const toolbars = document.querySelectorAll('div[role="dialog"] , div.aDh, div.nH.Hd');
  toolbars.forEach((container) => {
    const sendButton = container.querySelector('div[role="button"][data-tooltip^="Send"]');
    if (!sendButton) return;
    const host = sendButton.parentElement;
    if (!host || host.querySelector(".pixeltrail-chip")) return;

    const chip = document.createElement("div");
    chip.className = "pixeltrail-chip";
    chip.textContent = "Track this email";
    chip.title = "Insert your PixelTrail tracking pixel";
    chip.addEventListener("click", async () => {
      const tracked = chip.dataset["tracked"] === "true";
      if (tracked) {
        removePixel();
        chip.dataset["tracked"] = "false";
        chip.textContent = "Track this email";
        return;
      }
      const stored = await chrome.storage.local.get("pixelUrl");
      const url = stored.pixelUrl;
      if (!url) {
        alert("Open the PixelTrail extension icon and paste a pixel link first.");
        return;
      }
      const result = insertPixel(url);

if (!result.ok) {
  alert(result.error);
  return;
}

// Get the tracking ID saved by popup.js
const storedTracking = await chrome.storage.local.get("trackingId");

if (!storedTracking.trackingId) {
  alert("Tracking ID is missing. Please create the tracking pixel again.");
  return;
}

// Track links already present in the draft
const linkResult = trackLinks(storedTracking.trackingId);

if (!linkResult.ok) {
  alert(linkResult.error);
  return;
}

chip.dataset["tracked"] = "true";
chip.textContent = "Tracking on ✓";

console.log(
  `PixelTrail: ${linkResult.trackedCount} link(s) tracked.`
);
    });
    host.appendChild(chip);
  });
}

chrome.runtime.onMessage.addListener((message, _sender, respond) => {

  if (message?.type === "PIXELTRAIL_INSERT") {

    const result = insertPixel(
      message.url,
      message.confirmSeenUrl
    );

    if (!result.ok) {
      respond(result);
      return true;
    }

    // Use the NEW tracking ID sent directly from popup.js
    const trackingId = message.trackingId;

    if (!trackingId) {
      respond({
        ok: false,
        error: "Tracking ID is missing."
      });
      return true;
    }

    // Track all normal links already present in the draft
    const linkResult = trackLinks(trackingId);

    if (!linkResult.ok) {
      respond(linkResult);
      return true;
    }

    console.log(
      `PixelTrail: ${linkResult.trackedCount} link(s) tracked using ${trackingId}`
    );

    respond({
      ok: true,
      trackedCount: linkResult.trackedCount
    });

    return true;
  }

  if (message?.type === "PIXELTRAIL_REMOVE") {
    respond(removePixel());
    return true;
  }

  return true;
});

const observer = new MutationObserver(() => addChips());
observer.observe(document.documentElement, { childList: true, subtree: true });
addChips();
