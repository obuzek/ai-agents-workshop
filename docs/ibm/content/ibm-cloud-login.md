# IBM Cloud login

!!! tip "IBM Cloud access link: [ibm.biz/txc26-4217](https://ibm.biz/txc26-4217)"
    Sign in there with your workshop seat's username and password. It takes you to the workshop's IBM Cloud account. Step-by-step instructions are below.

You use **two different logins** today:

| For | Log in with |
|---|---|
| IBM Bob | **Your own IBMid** |
| IBM Cloud (your agent, your API key) | **A workshop seat login** from the list below |

Don't use your own IBMid for IBM Cloud. Your IBMid isn't in the workshop's IBM Cloud account, and IBM Cloud will ask you to create a new account.

## 1. Pick your seat

Take the seat your instructor gives you. Each seat is for one person.

<div id="seat-list" hidden markdown>

<table>
<thead><tr><th>Seat</th><th>Username</th><th>Password</th></tr></thead>
<tbody id="seat-rows"></tbody>
</table>

</div>

<p id="seat-list-missing">Your instructor gives you your seat's username and password.</p>

## 2. Log in to IBM Cloud with the access link

Use this link. Don't start from cloud.ibm.com.

<p style="font-size:1.3em"><strong><a href="https://ibm.biz/txc26-4217" target="_blank" rel="noopener">ibm.biz/txc26-4217</a></strong></p>

1. Open a **private / incognito browser window**, so your own IBMid doesn't sign you in by accident.
2. Open **[ibm.biz/txc26-4217](https://ibm.biz/txc26-4217)** in that window.
3. You see a sign-in page that says **Powered by IBM Technology Zone**. Enter your seat's **Username** and **Password**, then click **Sign in**.
4. The first time, IBM may show an **Important Notices** page about IBMid accounts. Scroll down and click **Proceed**. If a cookie banner appears, click **Accept All** or close it.
5. You land on the **IBM Cloud dashboard**.

!!! warning "Seeing \"Create an IBM Cloud account\"?"
    You signed in somewhere other than the access link, or with your own IBMid. Close the window, open a new private window, and start again from step 2. Don't fill in the account form.

## 3. Create your API key

Your code talks to IBM Cloud with an **API key**: a long secret string that acts as your seat. Create it in the IBM Cloud dashboard from step 2:

1. In the **top menu bar**, open the **Manage** dropdown and choose **Access (IAM)**.
2. In the **IAM menu on the left**, find the **Manage identities** heading and click **API keys** underneath it.
3. Click **Create**.
4. Give the key a name, such as `ai-agents-workshop`, and click **Create**.
5. Click **Copy** to copy the key. Leave this browser tab open until the installer has accepted it.

!!! warning "You only see the key once"
    IBM Cloud shows the key only when you create it. If you close the dialog before the installer accepts it, delete that key and create a new one.

Now go back to the [Prerequisites](prerequisites.md#run-the-installer) and run the installer. It asks for this key.

<script>
  // Seat logins come from the workshop backend, not from this page, and stop being served after the workshop.
  fetch("https://workshop-ehr.2g7six4hbjvx.us-south.codeengine.appdomain.cloud/workshop/seats", { cache: "no-store" })
    .then(r => (r.ok ? r.json() : null))
    .then(info => {
      if (!info || !Array.isArray(info.seats) || !info.seats.length) return;
      const rows = document.getElementById("seat-rows");
      info.seats.forEach((seat, i) => {
        const tr = document.createElement("tr");
        [String(i + 1).padStart(2, "0"), seat.username, seat.password].forEach((value, col) => {
          const td = document.createElement("td");
          if (col === 0) { td.textContent = value; } else { const code = document.createElement("code"); code.textContent = value; td.appendChild(code); }
          tr.appendChild(td);
        });
        rows.appendChild(tr);
      });
      document.getElementById("seat-list").hidden = false;
      document.getElementById("seat-list-missing").hidden = true;
    })
    .catch(() => {});
</script>
