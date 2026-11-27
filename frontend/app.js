// Keep your live Render backend URL here:
const API_BASE = "https://check-in-kiosk-client.onrender.com";

const form = document.getElementById("checkin-form");
const errorBox = document.getElementById("error-box");
const submitBtn = document.getElementById("submit-btn");
const modalBackdrop = document.getElementById("modal-backdrop");
const redeemBtn = document.getElementById("redeem-btn");
const doneBtn = document.getElementById("done-btn");

let lastCheckedInPhone = "";

const MOTIVATIONAL_NOTES = [
  "Thank you for trusting us with your brows today! ✨",
  "You're glowing already — thank you for checking in! 💖",
  "Self-care looks amazing on you. Thanks for visiting! 🌸",
  "Great brows, great day! Thank you for stopping by! 💕",
];

function showError(msg) {
  errorBox.textContent = `Oops! ${msg}`;
  errorBox.style.display = "block";
}

function clearError() {
  errorBox.textContent = "";
  errorBox.style.display = "none";
}

function getCustomerLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Your browser does not support location check-ins."));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        });
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          reject(
            new Error(
              "Please allow Location Access in your browser settings so we can verify you're at the salon!"
            )
          );
        } else {
          reject(
            new Error(
              "Could not verify your location. Please step closer to the front window or try again."
            )
          );
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      }
    );
  });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();
  submitBtn.disabled = true;

  const name = document.getElementById("name").value;
  const phoneNumber = document.getElementById("phone").value;
  const referredPhone = document.getElementById("referred-phone").value.trim();

  try {
    submitBtn.textContent = "Verifying Location... 📍";
    const coords = await getCustomerLocation();

    submitBtn.textContent = "Checking You In... ✨";
    const response = await fetch(`${API_BASE}/api/checkin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        phone_number: phoneNumber,
        referred_phone: referredPhone || null,
        latitude: coords.latitude,
        longitude: coords.longitude,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Check-in failed");
    }

    lastCheckedInPhone = phoneNumber;
    form.reset();

    const modalTitle = document.getElementById("modal-title");
    const modalThanks = document.getElementById("modal-thanks");
    const modalVisits = document.getElementById("modal-visits");
    const promoBox = document.getElementById("promo-box");
    const referralBox = document.getElementById("referral-box");
    const rewardBox = document.getElementById("reward-box");
    const rewardText = document.getElementById("reward-text");

    modalTitle.textContent = data.is_new_user
      ? `Welcome, ${data.name}! 🌸`
      : `Welcome back, ${data.name}! 💖`;

    const randomNote =
      MOTIVATIONAL_NOTES[Math.floor(Math.random() * MOTIVATIONAL_NOTES.length)];
    modalThanks.textContent = randomNote;

    modalVisits.textContent =
      data.visits_away === 0
        ? `🎉 Visit #${data.visits_count} — You just unlocked a loyalty reward!`
        : `✨ Visit #${data.visits_count} — Only ${data.visits_away} more visit(s) until your next reward!`;

    if (data.promo && data.promo.promo_eligible) {
      promoBox.textContent = `☀️ ${data.promo.promo_message}`;
      promoBox.style.display = "block";
    } else {
      promoBox.style.display = "none";
    }

    if (data.referral_message) {
      referralBox.textContent = `🎀 ${data.referral_message}`;
      referralBox.style.display = "block";
    } else {
      referralBox.style.display = "none";
    }

    if (data.available_discounts > 0) {
      rewardText.textContent = `🎁 You have ${data.available_discounts} reward discount(s) ready to use!`;
      rewardBox.style.display = "block";
    } else {
      rewardBox.style.display = "none";
    }

    modalBackdrop.classList.add("open");
  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "✨ Check In & Glow ✨";
  }
});

redeemBtn.addEventListener("click", async () => {
  if (!lastCheckedInPhone) return;
  redeemBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/redeem`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: lastCheckedInPhone }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Failed to redeem discount");
    }

    document.getElementById("redeem-status").textContent = `🎉 ${data.message} Enjoy your glow!`;

    const rewardBox = document.getElementById("reward-box");
    const rewardText = document.getElementById("reward-text");
    if (data.available_discounts > 0) {
      rewardText.textContent = `🎀 You have ${data.available_discounts} reward discount(s) left!`;
    } else {
      rewardBox.style.display = "none";
    }
  } catch (err) {
    showError(err.message);
  } finally {
    redeemBtn.disabled = false;
  }
});

doneBtn.addEventListener("click", () => {
  modalBackdrop.classList.remove("open");
  document.getElementById("redeem-status").textContent = "";
});