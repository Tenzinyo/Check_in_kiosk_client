// Locally use http://127.0.0.1:8000; later swap to your Render https:// URL!
const API_BASE = "https://check-in-kiosk-client.onrender.com";

const form = document.getElementById("checkin-form");
const errorBox = document.getElementById("error-box");
const submitBtn = document.getElementById("submit-btn");
const modalBackdrop = document.getElementById("modal-backdrop");
const redeemBtn = document.getElementById("redeem-btn");
const doneBtn = document.getElementById("done-btn");

let lastCheckedInPhone = "";

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.style.display = "block";
}

function clearError() {
  errorBox.textContent = "";
  errorBox.style.display = "none";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();
  submitBtn.disabled = true;
  submitBtn.textContent = "Checking In...";

  const name = document.getElementById("name").value;
  const phoneNumber = document.getElementById("phone").value;
  const referredPhone = document.getElementById("referred-phone").value.trim();

  try {
    // TODO 1: Send POST request to `${API_BASE}/api/checkin`
    // - headers: { "Content-Type": "application/json" }
    // - body: JSON.stringify({
    //     name,
    //     phone_number: phoneNumber,
    //     referred_phone: referredPhone || null,
    //   })
    const response = await fetch(`${API_BASE}/api/checkin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        name,
        phone_number: phoneNumber,
        referred_phone: referredPhone || null,
    }),
    });
    const data = await response.json()

    // TODO 2: Parse JSON (`const data = await response.json()`).
    // If `!response.ok`, throw `new Error(data.detail || "Check-in failed")`.
    if (!response.ok){
        throw new Error(data.detail || "Check-in failed");
    }

    // TODO 3: Save `lastCheckedInPhone = phoneNumber`, reset the form (`form.reset()`),
    lastCheckedInPhone = phoneNumber;
    form.reset();
    // and populate the modal elements (`#modal-title`, `#modal-visits`, `#promo-box`, `#reward-box`),
    // then open the modal with `modalBackdrop.classList.add("open")`.
    const modalTitle = document.getElementById("modal-title");
    const modalVisits = document.getElementById("modal-visits");
    const promoBox = document.getElementById("promo-box");
    const rewardBox = document.getElementById("reward-box");
    const rewardText = document.getElementById("reward-text");

    modalTitle.textContent = `${data.is_new_user ? "Welcome" : "Welcome back"}, ${data.name}!`;
    modalVisits.textContent = `Visit #${data.visits_count} — ${data.visits_away} more visit(s) until your next reward.`;

    if (data.promo && data.promo.promo_eligible){
        promoBox.textContent = data.promo.promo_message;
        promoBox.style.display = "block";
    } else{
        promoBox.style.display = "none"
    }

    if (data.available_discounts > 0){
        rewardText.textContent = `You have ${data.available_discounts} discount(s) available!`;
        rewardBox.style.display = "block";
    } else {
        rewardBox.style.display = "none";
    }
    
    modalBackdrop.classList.add("open");

  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Check In";
  }
});

redeemBtn.addEventListener("click", async () => {
  if (!lastCheckedInPhone) return;
  redeemBtn.disabled = true;

  try {
    // TODO 4: Send POST request to `${API_BASE}/api/redeem`
    const response = await fetch(`${API_BASE}/api/redeem`, {
        method: "POST",
        headers : {
            "Content-Type": "application/json",
        },
        body : JSON.stringify({ phone_number: lastCheckedInPhone }),

    });
    const data = await response.json();
    if (!response.ok){
        throw new Error(data.detail || "Failed to redeem discount");
    }
    document.getElementById("redeem-status").textContent = data.message;

    const rewardBox = document.getElementById("reward-box");
    const rewardText = document.getElementById("reward-text");
    if (data.available_discounts > 0) {
      rewardText.textContent = `You have ${data.available_discounts} discount(s) available!`;
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