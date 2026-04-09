# Jenkins Access & Verification Guide

Complete step-by-step guide to access Jenkins, reload pipeline, and verify all 9 stages.

---

## 📍 Step 1: Open Jenkins in Browser

**URL:** `http://172.83.83.156:8080`

```
http://172.83.83.156:8080
```

**Expected Result:**
- Jenkins login page appears OR
- Jenkins dashboard (if already logged in)

**Screenshot to Take:** Jenkins homepage with "ml-autoscaling-pipeline" visible in left menu

---

## 🔐 Step 2: Login (if needed)

**Username:** jenkins  
**Password:** Check your notes or ask admin

Or look for credentials at:
- Jenkins Master → /var/lib/jenkins/secrets/initialAdminPassword

**If you can't login:**
```bash
# SSH to master (if you have access)
ssh -i kub-cluster-key.pem ubuntu@10.0.1.7

# Check Jenkins is running
sudo systemctl status jenkins

# Get initial password
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

**Screenshot to Take:** Successfully logged in to Jenkins dashboard

---

## 🔍 Step 3: Find Your Pipeline Job

**In Jenkins Dashboard:**

1. Look in **left sidebar** for **"ml-autoscaling-pipeline"** OR **"HA-K8S1"**
2. **Click** on the job name

**Or use direct URL:**
```
http://172.83.83.156:8080/job/ml-autoscaling-pipeline/
OR
http://172.83.83.156:8080/job/HA-K8S1/
```

**Expected Result:**
- Job dashboard opens
- Shows "Build History" on left
- Shows "Build Now" button

**Screenshot to Take:** Job dashboard with build history visible

---

## ⚙️ Step 4: Open Configure

**Click the "Configure" button:**
- Left sidebar → **Configure**
- OR Top menu → **Configure**

**Expected Result:**
- Job configuration page opens
- Shows various sections (General, Build Triggers, Pipeline, etc.)

**Screenshot to Take:** Configure page opened

---

## 📝 Step 5: Find Pipeline Section

**Scroll DOWN to find the "Pipeline" section**

You should see:

```
Definition: Pipeline script from SCM

SCM
├─ Git
├─ Repository URL: https://github.com/prerna3640/HA-K8S1.git
├─ Branch: */main
└─ Script Path: Jenkinsfile
```

**What to verify:**
- ✅ Repository URL = `https://github.com/prerna3640/HA-K8S1.git`
- ✅ Branch = `*/main` (or `main`)
- ✅ Script Path = `Jenkinsfile`

**If any are wrong, fix them!**

**Screenshot to Take:** Pipeline configuration section showing correct values

---

## 💾 Step 6: Save Configuration

**Scroll to BOTTOM and click "Save"**

**Expected Result:**
- Configuration page closes
- You're back at job dashboard
- Jenkins message: "Configuration saved" or similar

**What happens:**
- Jenkins fetches **fresh Jenkinsfile from GitHub** (branch: main)
- New stages (Unit Tests, Static Analysis, ArgoCD) are now loaded

**Screenshot to Take:** Job dashboard after save

---

## ▶️ Step 7: Trigger New Build

**Click "Build Now" button**

**Expected Result:**
- New build starts (Build #3, #4, #5, etc.)
- In Build History → new build appears

**What to wait for:**
- Build completes (5-10 minutes)
- All stages should turn green ✅

**Screenshot to Take:** Build History showing new build running

---

## 📊 Step 8: View Stage View (Most Important!)

**After build completes:**

**Click on the latest build** (top of Build History)

**Expected Result:**
- Build details page opens
- Shows console output

**Then click "Stage View" or "Stages"** (usually in left sidebar or top)

**Expected Result:**
- Visual pipeline with boxes for each stage
- Should show **9 stages**:

```
┌─────────────────────────────────────────────────────────┐
│ Checkout │ Unit    │ Static   │ Build ML │ Build      │
│          │ Tests   │ Analysis │Predictor │ Scaler    │
├─────────────────────────────────────────────────────────┤
│ Transfer │ Update  │ ArgoCD   │ Verify   │ Post      │
│ Workers  │ Manifests│ Sync    │          │ Actions   │
└─────────────────────────────────────────────────────────┘
```

**All should be GREEN ✅**

**Screenshot to Take:** Stage View with all 9 green stages - THIS IS YOUR MAIN PROOF!

---

## ✅ Step 9: Verify Each Stage

**Click on each stage** to see its output:

### **Stage 1: Checkout**
```
Output should show:
✓ git clone https://github.com/prerna3640/HA-K8S1.git
✓ Checking out branch main
```

### **Stage 2: Unit Tests** ← NEW
```
Output should show:
=== Running Unit Tests ===
test_model.py::test_ensemble_predictor_training PASSED
test_model.py::test_prophet_predictor_training PASSED
test_predictor_api.py::test_health_endpoint PASSED
...
===== 21 passed in X.XXs =====
Coverage: 80%+
```

### **Stage 3: Static Analysis** ← NEW
```
Output should show:
=== Running flake8 Static Analysis ===
Total errors: 0
=== Static Analysis Complete ===
```

### **Stage 4: Build ML Predictor**
```
Output should show:
nerdctl build -t ml-predictor:BUILD_NUMBER
✓ Image built successfully
```

### **Stage 5: Build Predictive Scaler**
```
Output should show:
nerdctl build -t predictive-scaler:BUILD_NUMBER
✓ Image built successfully
```

### **Stage 6: Transfer to Workers**
```
Output should show:
=== Transferring to worker-data (10.0.1.114) ===
✓ Image imported to worker-data
=== Transferring to worker-app (10.0.1.105) ===
✓ Image imported to worker-app
```

### **Stage 7: Update GitOps Manifests** ← NEW
```
Output should show:
=== Updating image tags in K8s manifests ===
[main BUILD_NUMBER] ci: update image tags to build-BUILD_NUMBER
✓ Manifests updated and pushed to GitHub
```

### **Stage 8: ArgoCD Sync** ← NEW
```
Output should show:
=== Triggering ArgoCD sync ===
✓ Application ml-predictor synced
✓ Application predictive-scaler synced
```

### **Stage 9: Verify**
```
Output should show:
=== Build #BUILD_NUMBER Verification ===
ml-predictor-XXXX Running
predictive-scaler-XXXX Running
=== ArgoCD Applications ===
ml-predictor Synced
predictive-scaler Synced
```

**Screenshot to Take:** Console output showing all green stages

---

## 🔗 Full Console Output

**Click "Full Log" or "Console Output"** to see entire build output:

**Key things to look for:**

```
✓ Checkout successful
✓ Running Unit Tests
  test_model.py .................... PASSED
  test_predictor_api.py ............ PASSED
  21 tests passed ✓
✓ Running Static Analysis
  0 errors found ✓
✓ Building ML Predictor image
✓ Building Predictive Scaler image
✓ Transferring to workers
✓ Updating manifests on GitHub
✓ Syncing ArgoCD
✓ Verification complete
```

**Screenshot to Take:** Full console log showing successful build

---

## 📱 What to Show Your Teacher

**Take these 3 key screenshots:**

1. **Stage View** - All 9 stages in green
2. **Unit Tests Output** - 21 tests passing
3. **Static Analysis Output** - 0 errors

**Tell your teacher:**
> "Before my work, the pipeline only built and deployed. Now it:
> - ✅ Runs 21 unit tests (80% coverage)
> - ✅ Checks code quality (PEP 8, 0 errors)
> - ✅ Automatically syncs to Kubernetes via ArgoCD
> - ✅ Complete CI/CD pipeline for ML research!"

---

## 🚨 Troubleshooting

### **Problem: Still showing old stages (< 9 stages)**

**Solution:**
1. Clear Jenkins cache: `Configure` → `Save` (without changes)
2. Wait 30 seconds
3. Click `Build Now` again
4. Check if new build has 9 stages

### **Problem: Build fails**

**Check:**
1. Click on failed stage
2. Read error message
3. Common issues:
   - ❌ Git credentials missing → Add GitHub token to Jenkins
   - ❌ Docker/nerdctl not available → Check worker nodes
   - ❌ Python dependencies missing → Check requirements.txt
   - ❌ SSH key for workers not found → Check `/var/lib/jenkins/.ssh/`

### **Problem: Tests fail**

**Check:**
```bash
# SSH to master and run tests locally
ssh ubuntu@10.0.1.7
cd /var/lib/jenkins/workspace/ml-autoscaling-pipeline/ml-predictor
python3 -m pytest tests/ -v
```

### **Problem: Cannot access Jenkins**

**Try these URLs:**
- `http://172.83.83.156:8080` (HTTP)
- `http://10.0.1.7:8080` (Internal IP)
- `https://172.83.83.156:8443` (HTTPS, if configured)

**Check Jenkins is running:**
```bash
ssh ubuntu@10.0.1.7
sudo systemctl status jenkins
```

---

## ✅ Final Checklist

- [ ] Opened Jenkins at http://172.83.83.156:8080
- [ ] Successfully logged in
- [ ] Found ml-autoscaling-pipeline job
- [ ] Clicked Configure
- [ ] Verified Pipeline section has correct GitHub repo
- [ ] Clicked Save
- [ ] Clicked Build Now
- [ ] Waited for build to complete
- [ ] Viewed Stage View
- [ ] Saw all 9 stages in green ✅
- [ ] Clicked on Unit Tests stage
- [ ] Saw "21 tests passed" ✓
- [ ] Clicked on Static Analysis stage
- [ ] Saw "0 errors" ✓
- [ ] Took screenshots of Stage View
- [ ] Took screenshots of Unit Tests output
- [ ] Took screenshots of Static Analysis output

---

## 🎯 Success Criteria

Your pipeline is correctly configured when:

✅ Jenkins shows **9 stages** (not 6 or fewer)  
✅ **Stage 2: Unit Tests** exists and passes  
✅ **Stage 3: Static Analysis** exists and shows 0 errors  
✅ **Stage 8: ArgoCD Sync** exists and syncs successfully  
✅ All stages turn **GREEN** (not red)  
✅ Build completes in ~5-10 minutes  

If all these are true → **Your CI/CD pipeline is working perfectly!** 🚀

---

## 📸 Screenshot Template

When taking screenshots, include:

```
[Screenshot 1] Jenkins Login
- URL: http://172.83.83.156:8080
- Status: Logged in ✓

[Screenshot 2] Job Dashboard
- Job name visible
- Build History shows recent builds

[Screenshot 3] Configure Page
- Pipeline section visible
- Repository URL: https://github.com/prerna3640/HA-K8S1.git
- Branch: */main
- Script Path: Jenkinsfile

[Screenshot 4] Stage View (MOST IMPORTANT)
- Shows all 9 stages in boxes
- All boxes are GREEN ✅
- Stages labeled: Checkout, Unit Tests, Static Analysis, Build ML, Build Scaler, Transfer, Update Manifests, ArgoCD Sync, Verify

[Screenshot 5] Unit Tests Output
- Shows: "21 passed"
- Shows: "Coverage: 80%+"

[Screenshot 6] Static Analysis Output
- Shows: "Total errors: 0"
- Shows: "=== Static Analysis Complete ==="
```

---

Good luck! Follow these steps and you'll have perfect proof of your CI/CD pipeline! 🎉
