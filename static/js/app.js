const createEventButton = document.querySelector("#create-event-button");
const cancelEventButton = document.querySelector("#cancel-event-button");
const eventForm = document.querySelector("#event-form");
const statusMessage = document.querySelector("#status-message");

createEventButton.addEventListener("click", () => {
    eventForm.hidden = false;
    statusMessage.textContent = "";
    document.querySelector("#event-name").focus();
});

cancelEventButton.addEventListener("click", () => {
    eventForm.reset();
    eventForm.hidden = true;
    statusMessage.textContent = "";
});

eventForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    statusMessage.textContent = "Saving...";

    const formData = new FormData(eventForm);
    const eventData = Object.fromEntries(formData.entries());

    try {
        const response = await fetch("/api/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(eventData),
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not save the event.");
        }

        eventForm.reset();
        eventForm.hidden = true;
        window.location.assign(result.event.url);
    } catch (error) {
        statusMessage.textContent = error.message;
    }
});
