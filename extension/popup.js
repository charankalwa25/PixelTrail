const recipientInput = document.getElementById("recipient");
const subjectInput = document.getElementById("subject");
const status = document.getElementById("status");

function say(text, ok = true) {
  status.textContent = text;
  status.style.color = ok ? "#35d492" : "#ff8080";
}


// Get the currently active Gmail tab
async function getGmailTab() {
  const tabs = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  const tab = tabs[0];

  if (!tab || !tab.url || !tab.url.startsWith("https://mail.google.com/")) {
    say("Open Gmail in this tab first.", false);
    return null;
  }

  return tab;
}


// Send a message to content.js
async function sendToTab(message) {

  const tab = await getGmailTab();

  if (!tab) {
    return false;
  }

  try {

    const result = await chrome.tabs.sendMessage(
      tab.id,
      message
    );

    if (!result || !result.ok) {
      say(
        result?.error || "Could not reach the Gmail draft.",
        false
      );

      return false;
    }

    return true;

  } catch (error) {

    console.error(error);

    say(
      "Reload the Gmail tab and try again.",
      false
    );

    return false;
  }
}


// Create tracking ID through our FastAPI backend
async function createTrackedEmail() {

  const recipient = recipientInput.value.trim();
  const subject = subjectInput.value.trim();

  if (!recipient) {
    say("Enter the recipient email.", false);
    return;
  }

  if (!subject) {
    say("Enter the email subject.", false);
    return;
  }

  say("Creating tracking pixel...");

  try {

    const response = await fetch(
      "https://pixeltrail.onrender.com/emails",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          recipient: recipient,
          subject: subject
        })
      }
    );

    if (!response.ok) {
      throw new Error(
        `Backend returned ${response.status}`
      );
    }

    const data = await response.json();

    console.log("PixelTrail backend response:", data);

    const pixelUrl = data.tracking_pixel_url;

    if (!pixelUrl) {
      say("Backend did not return a tracking pixel URL.", false);
      return;
    }

    // Save the tracking information
    await chrome.storage.local.set({
  pixelUrl: pixelUrl,
  trackingId: data.tracking_id,
  confirmSeenUrl: data.confirm_seen_url,
  recipient: recipient,
  subject: subject
  });

    say("Tracking pixel created. Inserting...");

    // Tell Gmail content script to insert the pixel
    const result = await sendToTab({
  type: "PIXELTRAIL_INSERT",
  url: pixelUrl,
  confirmSeenUrl: data.confirm_seen_url,
  trackingId: data.tracking_id
 });

    if (result) {
      say("Pixel inserted — send your email normally.");
    }

  } catch (error) {

    console.error("PixelTrail error:", error);

    say(
      "Could not connect to PixelTrail backend. Is FastAPI running?",
      false
    );
  }
}


// Remove tracking pixel
async function removePixel() {

  const result = await sendToTab({
    type: "PIXELTRAIL_REMOVE"
  });

  if (result) {
    say("Pixel removed.");
  }
}


// Create & Insert button
document
  .getElementById("insert")
  .addEventListener("click", createTrackedEmail);


// Remove button
document
  .getElementById("remove")
  .addEventListener("click", removePixel);