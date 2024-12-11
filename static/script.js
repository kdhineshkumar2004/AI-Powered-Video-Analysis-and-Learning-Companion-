document.getElementById("youtubeForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const urlInput = document.getElementById("url").value;
    const responseMessage = document.getElementById("responseMessage");

    responseMessage.textContent = "Processing... Please wait.";

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url: urlInput }),
        });

        if (response.ok) {
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = "analysis.pdf";
            document.body.appendChild(a);
            a.click();
            a.remove();
            responseMessage.textContent = "Analysis complete! PDF downloaded.";
        } else {
            const errorData = await response.json();
            responseMessage.textContent = `Error: ${errorData.error}`;
        }
    } catch (error) {
        responseMessage.textContent = `An unexpected error occurred: ${error.message}`;
    }
});
