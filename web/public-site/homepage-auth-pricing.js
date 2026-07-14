/*
Stock & Stir homepage wiring: login, 7-day trial, and updated pricing.
Load this file immediately before </body> in index.html:
<script src="homepage-auth-pricing.js"></script>
*/
document.addEventListener("DOMContentLoaded",()=> {
  const signup="login.html?mode=signup";
  const login="login.html";

  document.querySelectorAll("a").forEach(a=>{
    const t=(a.textContent||"").trim().toLowerCase();
    if(t==="log in") a.href=login;
    if(t.includes("start free")||t.includes("start with my kitchen")||t.includes("find my dinner")) a.href=signup;
  });

  const pricing=document.querySelector("#pricing");
  if(!pricing) return;

  pricing.innerHTML=`
    <div class="section-title">Simple Pricing</div>
    <div style="max-width:1100px;margin:0 auto 28px;padding:18px 22px;border:1px solid var(--gold);border-radius:14px;background:#1a211f;text-align:center;color:#f8efe3">
      <strong>Try Stock & Stir free for 7 days.</strong>
      Explore My Kitchen, generate meals, and see whether it earns a place in your household.
    </div>
    <div class="plans">
      <div class="plan">
        <h3>Monthly</h3>
        <div class="price">$10 <small>/month</small></div>
        <p style="color:var(--gold);font-weight:700">About $0.33 per day</p>
        <ul class="checklist">
          <li>7-day free trial</li>
          <li>Full My Kitchen household memory</li>
          <li>Recipe choices shaped around your inventory</li>
          <li>Cancel anytime</li>
        </ul>
        <a class="btn btn-outline wide" href="login.html?mode=signup&plan=monthly">Start 7-Day Free Trial</a>
      </div>
      <div class="plan featured">
        <h3>Annual — Best Value</h3>
        <div class="price">$100 <small>/year</small></div>
        <p style="color:var(--gold);font-weight:700">Only about $0.27 per day</p>
        <ul class="checklist">
          <li>7-day free trial</li>
          <li>Everything in Monthly</li>
          <li>Two months included</li>
          <li>One simple annual payment</li>
        </ul>
        <a class="btn btn-primary wide" href="login.html?mode=signup&plan=annual">Start 7-Day Free Trial</a>
      </div>
      <div class="plan">
        <h3>Simple & Secure</h3>
        <ul class="checklist">
          <li>One complete Stock & Stir product</li>
          <li>No stripped-down pantry tier</li>
          <li>Secure billing through Stripe</li>
          <li>Manage or cancel through your account</li>
        </ul>
        <a class="btn btn-outline wide" href="login.html">Already a member? Log in</a>
      </div>
    </div>`;
});