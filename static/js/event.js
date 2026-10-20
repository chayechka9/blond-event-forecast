const eventPage = document.querySelector(".event-page");
const eventId = eventPage.dataset.eventId;
const editEventButton = document.querySelector("#edit-event-button");
const deleteEventButton = document.querySelector("#delete-event-button");
const editEventForm = document.querySelector("#edit-event-form");
const cancelEventEdit = document.querySelector("#cancel-event-edit");
const editEventStatus = editEventForm.querySelector(".form-status");

editEventButton.addEventListener("click", () => {
    editEventForm.hidden = false;
    editEventButton.hidden = true;
    editEventForm.querySelector("input[name='name']").focus();
});

cancelEventEdit.addEventListener("click", () => {
    editEventForm.reset();
    editEventForm.hidden = true;
    editEventButton.hidden = false;
    editEventStatus.textContent = "";
});

editEventForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    editEventStatus.textContent = "Saving...";

    const formData = new FormData(editEventForm);
    const eventData = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(`/api/events/${eventId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(eventData),
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not update the event.");
        }

        window.location.reload();
    } catch (error) {
        editEventStatus.textContent = error.message;
    }
});

deleteEventButton.addEventListener("click", async () => {
    const eventName = document.querySelector(".event-header h1").textContent.trim();
    const confirmed = window.confirm(
        `Delete “${eventName}” and all of its expenses and revenue?`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/api/events/${eventId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            const result = await response.json();
            throw new Error(result.error || "Could not delete the event.");
        }

        window.location.assign("/");
    } catch (error) {
        window.alert(error.message);
    }
});

document.querySelectorAll(".expense-category").forEach((category) => {
    const addButton = category.querySelector(".add-item-button");
    const cancelButton = category.querySelector(".cancel-item-button");
    const form = category.querySelector(".expense-form");
    const status = category.querySelector(".form-status");

    addButton.addEventListener("click", () => {
        form.hidden = false;
        addButton.hidden = true;
        form.querySelector("input[name='name']").focus();
    });

    cancelButton.addEventListener("click", () => {
        form.reset();
        form.hidden = true;
        addButton.hidden = false;
        status.textContent = "";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "Saving...";

        const formData = new FormData(form);
        const itemData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch(`/api/events/${eventId}/expenses`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(itemData),
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not save the item.");
            }

            window.location.reload();
        } catch (error) {
            status.textContent = error.message;
        }
    });
});

document.querySelectorAll(".expense-item").forEach((item) => {
    const itemId = item.dataset.itemId;
    const summary = item.querySelector(".expense-item-summary");
    const editButton = item.querySelector(".edit-item-button");
    const deleteButton = item.querySelector(".delete-item-button");
    const editForm = item.querySelector(".edit-expense-form");
    const cancelButton = item.querySelector(".cancel-edit-button");
    const status = item.querySelector(".form-status");

    editButton.addEventListener("click", () => {
        summary.hidden = true;
        editForm.hidden = false;
        editForm.querySelector("input[name='name']").focus();
    });

    cancelButton.addEventListener("click", () => {
        editForm.reset();
        editForm.hidden = true;
        summary.hidden = false;
        status.textContent = "";
    });

    editForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "Saving...";

        const formData = new FormData(editForm);
        const itemData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch(`/api/events/${eventId}/expenses/${itemId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(itemData),
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not update the item.");
            }

            window.location.reload();
        } catch (error) {
            status.textContent = error.message;
        }
    });

    deleteButton.addEventListener("click", async () => {
        const itemName = item.querySelector("strong").textContent.trim();
        const confirmed = window.confirm(`Delete “${itemName}”?`);

        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch(`/api/events/${eventId}/expenses/${itemId}`, {
                method: "DELETE",
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || "Could not delete the item.");
            }

            window.location.reload();
        } catch (error) {
            window.alert(error.message);
        }
    });
});

const addRevenueCategoryButton = document.querySelector("#add-revenue-category-button");
const cancelRevenueCategoryButton = document.querySelector("#cancel-revenue-category-button");
const revenueCategoryForm = document.querySelector("#revenue-category-form");
const revenueCategoryStatus = revenueCategoryForm.querySelector(".form-status");

addRevenueCategoryButton.addEventListener("click", () => {
    revenueCategoryForm.hidden = false;
    addRevenueCategoryButton.hidden = true;
    revenueCategoryForm.querySelector("input[name='name']").focus();
});

cancelRevenueCategoryButton.addEventListener("click", () => {
    revenueCategoryForm.reset();
    revenueCategoryForm.hidden = true;
    addRevenueCategoryButton.hidden = false;
    revenueCategoryStatus.textContent = "";
});

revenueCategoryForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    revenueCategoryStatus.textContent = "Saving...";

    const formData = new FormData(revenueCategoryForm);
    const categoryData = Object.fromEntries(formData.entries());

    try {
        const response = await fetch(`/api/events/${eventId}/revenue-categories`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(categoryData),
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not save the category.");
        }

        window.location.reload();
    } catch (error) {
        revenueCategoryStatus.textContent = error.message;
    }
});

document.querySelectorAll(".revenue-category").forEach((category) => {
    const categoryId = category.dataset.categoryId;
    const categorySummary = category.querySelector(".revenue-category-summary");
    const editCategoryButton = category.querySelector(".edit-revenue-category-button");
    const deleteCategoryButton = category.querySelector(".delete-revenue-category-button");
    const editCategoryForm = category.querySelector(".edit-revenue-category-form");
    const cancelCategoryEdit = category.querySelector(".cancel-revenue-category-edit");
    const editCategoryStatus = editCategoryForm.querySelector(".form-status");
    const addButton = category.querySelector(".add-revenue-item-button");
    const cancelButton = category.querySelector(".cancel-revenue-item-button");
    const form = category.querySelector(".revenue-item-form");
    const status = form.querySelector(".form-status");

    editCategoryButton.addEventListener("click", () => {
        categorySummary.hidden = true;
        editCategoryForm.hidden = false;
        editCategoryForm.querySelector("input[name='name']").focus();
    });

    cancelCategoryEdit.addEventListener("click", () => {
        editCategoryForm.reset();
        editCategoryForm.hidden = true;
        categorySummary.hidden = false;
        editCategoryStatus.textContent = "";
    });

    editCategoryForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        editCategoryStatus.textContent = "Saving...";

        const formData = new FormData(editCategoryForm);
        const categoryData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch(
                `/api/events/${eventId}/revenue-categories/${categoryId}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(categoryData),
                }
            );
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not update the category.");
            }

            window.location.reload();
        } catch (error) {
            editCategoryStatus.textContent = error.message;
        }
    });

    deleteCategoryButton.addEventListener("click", async () => {
        const categoryName = category.querySelector("h3").textContent.trim();
        const confirmed = window.confirm(
            `Delete “${categoryName}” and all of its items?`
        );

        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch(
                `/api/events/${eventId}/revenue-categories/${categoryId}`,
                { method: "DELETE" }
            );

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || "Could not delete the category.");
            }

            window.location.reload();
        } catch (error) {
            window.alert(error.message);
        }
    });

    addButton.addEventListener("click", () => {
        form.hidden = false;
        addButton.hidden = true;
        form.querySelector("input[name='name']").focus();
    });

    cancelButton.addEventListener("click", () => {
        form.reset();
        form.hidden = true;
        addButton.hidden = false;
        status.textContent = "";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "Saving...";

        const formData = new FormData(form);
        const itemData = Object.fromEntries(formData.entries());

        try {
            const response = await fetch(
                `/api/events/${eventId}/revenue-categories/${categoryId}/items`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(itemData),
                }
            );
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not save the item.");
            }

            window.location.reload();
        } catch (error) {
            status.textContent = error.message;
        }
    });

    category.querySelectorAll(".revenue-item").forEach((item) => {
        const itemId = item.dataset.itemId;
        const summary = item.querySelector(".revenue-item-summary");
        const editButton = item.querySelector(".edit-revenue-item-button");
        const deleteButton = item.querySelector(".delete-revenue-item-button");
        const editForm = item.querySelector(".edit-revenue-item-form");
        const cancelEdit = item.querySelector(".cancel-revenue-item-edit");
        const editStatus = editForm.querySelector(".form-status");

        editButton.addEventListener("click", () => {
            summary.hidden = true;
            editForm.hidden = false;
            editForm.querySelector("input[name='name']").focus();
        });

        cancelEdit.addEventListener("click", () => {
            editForm.reset();
            editForm.hidden = true;
            summary.hidden = false;
            editStatus.textContent = "";
        });

        editForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            editStatus.textContent = "Saving...";

            const formData = new FormData(editForm);
            const itemData = Object.fromEntries(formData.entries());

            try {
                const response = await fetch(
                    `/api/events/${eventId}/revenue-categories/${categoryId}/items/${itemId}`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(itemData),
                    }
                );
                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || "Could not update the item.");
                }

                window.location.reload();
            } catch (error) {
                editStatus.textContent = error.message;
            }
        });

        deleteButton.addEventListener("click", async () => {
            const itemName = item.querySelector("strong").textContent.trim();
            const confirmed = window.confirm(`Delete “${itemName}”?`);

            if (!confirmed) {
                return;
            }

            try {
                const response = await fetch(
                    `/api/events/${eventId}/revenue-categories/${categoryId}/items/${itemId}`,
                    { method: "DELETE" }
                );

                if (!response.ok) {
                    const result = await response.json();
                    throw new Error(result.error || "Could not delete the item.");
                }

                window.location.reload();
            } catch (error) {
                window.alert(error.message);
            }
        });
    });
});
