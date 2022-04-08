/* script.js */

//conventient failure messages
const Fs = ([cF, rF, uF, dF] = ["create", "read", "update", "delete"].map(
  (op) => `failed to ${op} mail[s]`
));

/* wapi setup */
const wapi = wapiInit("https://auth.web10.app");
const sirs = [
  {
    service: "web10-docs-mail-demo",
    cross_origins: ["docs.web10.app", "localhost", "docs.localhost"],
    whitelist : [{username:".*",provider:".*",create:true}]//allows all users to write to you
  },
];
wapi.SMROnReady(sirs, []);
authButton.onclick = wapi.openAuthPortal;

/* web10 devPay */
const [seller, subscriptionTitle, price, url] = [
  "jacoby149",
  "mailer-premium",
  50,
  window.location.href,
];

/* message for current subscribers */
function displaySubscriberMessage() {
  subscriptionStatus.innerHTML = `subscribed! <button id="cancel"> cancel sub </button>`;
  cancel.onclick = () =>
    wapi
      .cancelSubscription(seller, subscriptionTitle)
      .then(() => window.location.reload())
      .catch((e) => {
        subscriptionStatus.innerHTML = `subscription cancellation failed...`;
      });
}

/* message for users that are not subscribed to onboard them */
function displayOnboardMessage() {
  subscriptionStatus.innerHTML = `not subscribed! <button id="checkout"> subscribe </button>`;
  checkout.onclick = () => wapi.checkout(seller, subscriptionTitle, price, url, url);
}

/* a front end weak subscription check [still lucrative!] */
function validSubscription(subscriptionData) {
  return (
    subscriptionData !== null &&
    parseInt(subscriptionData["price"]) === price &&
    subscriptionData["seller"] === seller &&
    subscriptionData["title"] === title
  );
}

/* The devpay functionality */
function devPay() {
  wapi
    .verifySubscription(seller, subscriptionTitle)
    .then((r) => {
      if (validSubscription(r["data"])) displaySubscriberMessage();
      else displayOnboardMessage();
    })
    .catch(
      (e) => (subscriptionStatus.innerHTML = `subscription check failed...`)
    );
}

function initApp() {
  authButton.innerHTML = "log out";
  authButton.onclick = () => {
    wapi.signOut();
    window.location.reload();
    devPay();
  };
  const t = wapi.readToken();
  message.innerHTML = `hello ${t["provider"]}/${t["username"]},<br>`;
  readMail();
  devPay();
}

if (wapi.isSignedIn()) initApp();
else wapi.authListen(initApp);

/* CRUD Calls */
function readMail() {
  wapi
    .read("web10-docs-mail-demo", {})
    .then((response) => displayMail(response.data))
    .catch((error) => (message.innerHTML = `${rF} : ${error}`));
}
function createMail(mail,user,provider) {
  const t = wapi.readToken();
  wapi
    .create("web10-docs-mail-demo", { mail: mail, date: String(new Date()),provider:t["provider"],username:t["username"] },user,provider)
    .then(() => {
      readMail();
      curr.value = "";
    })
    .catch(
      (error) => (message.innerHTML = `${cF} : ${error}`)
    );
}
function deleteMail(id) {
  wapi
    .delete("web10-docs-mail-demo", { _id: id })
    .then(readMail)
    .catch(
      (error) => (message.innerHTML = `${dF} : ${error.response.data.detail}`)
    );
}

/* display */
function displayMail(data) {
  function contain(mail) {
    return `<div style="margin-top:40px;margin-left:10px">
                <p style="font-family:monospace;">${mail.date}</p>
                <p style="font-family:monospace;">${mail.provider}/${mail.username}</p>                
                <i id="${mail._id}">${mail.mail}</i>
                <button onclick="deleteMail('${mail._id}')">Delete</button>
            </div>`;
  }
  mailview.innerHTML = data.map(contain).reverse().join(`<br>`);
}