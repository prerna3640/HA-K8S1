# Quick Fix for Jenkins Pipeline - Step by Step

Your issue is that **Jenkins is not showing the new 9 stages**. Here's the exact fix:

---

## 🔴 Problem You're Seeing:
- Jenkins shows only 6-7 stages (old pipeline)
- Stage 2 "Unit Tests" is NOT visible
- Stage 3 "Static Analysis" is NOT visible

## ✅ Solution:

### Step 1: Go Back to Job Page
Click the back button or go to:
```
http://<master-public-ip>:8080/job/ml-autoscaling-pipeline/
```

### Step 2: Click "Configure" (Left Sidebar)
The left sidebar should show:
- Status
- Changes
- **Configure** ← Click this
- Build Now
- etc.

### Step 3: Scroll DOWN to "Pipeline" Section

You should see:
```
Pipeline
├─ Definition: Pipeline script from SCM
└─ SCM: Git
   ├─ Repository URL: https://github.com/prerna3640/HA-K8S1.git
   ├─ Credentials: (if needed)
   ├─ Branch: */main
   └─ Script Path: Jenkinsfile
```

### Step 4: Check Script Path
- Make sure it says: **Jenkinsfile** (not "Jenkinsfile" with extra text)
- If it looks wrong, clear it and type: `Jenkinsfile`

### Step 5: Click "Save" Button (Bottom)
- This forces Jenkins to reload from GitHub
- Wait 5 seconds

### Step 6: Click "Build Now" (Left Sidebar)
- Jenkins will pull fresh Jenkinsfile from GitHub
- Build should start

### Step 7: Wait 2-3 minutes for build to complete

### Step 8: Click the Latest Build Number (in Build History)
- You should see the **new build** in Build History
- Click it

### Step 9: Look for "Stage View"
In the left sidebar or top menu, find:
- **Stage View** OR
- **Stages** OR  
- Just look at the build output

You should now see **9 stages** instead of 6!

---

## ✨ Expected Output

**If it worked**, you'll see boxes like this:

```
┌──────────┬──────────┬─────────────┬──────────────┬──────────────┐
│ Checkout │Unit Tests│   Static    │  Build ML    │  Build       │
│          │          │  Analysis   │  Predictor   │  Scaler      │
├──────────┼──────────┼─────────────┼──────────────┼──────────────┤
│ Transfer │  Update  │  ArgoCD     │   Verify     │              │
│ Workers  │ Manifests│   Sync      │              │              │
└──────────┴──────────┴─────────────┴──────────────┴──────────────┘
```

All boxes should be **GREEN** ✅

---

## 🔧 Alternative: Direct URL Navigation

Instead of clicking around, just copy-paste these URLs:

**1. Go to job:**
```
http://<master-public-ip>:8080/job/ml-autoscaling-pipeline/
```

**2. Go to configure:**
```
http://<master-public-ip>:8080/job/ml-autoscaling-pipeline/configure
```

**3. After saving, see Stage View of latest build:**
```
http://<master-public-ip>:8080/job/ml-autoscaling-pipeline/lastBuild/
```

---

## ❌ If Still Not Working

### Issue: Still showing old stages

**Root cause:** Jenkins cached the old Jenkinsfile in its workspace

**Solution: Hard reset Jenkins workspace**

1. Go to Configure (URL above)
2. Look for "Additional Behaviours" under Git
3. Click "**Add**" → "**Clean before checkout**"
4. Save
5. Build Now

This will delete Jenkins workspace and re-clone entire repo from GitHub with fresh Jenkinsfile.

---

## 📋 Checklist

- [ ] Navigated to job Configure page
- [ ] Found Pipeline → SCM section
- [ ] Verified Script Path = `Jenkinsfile`
- [ ] Clicked Save
- [ ] Clicked Build Now
- [ ] Waited 2-3 minutes for build
- [ ] Clicked on latest build
- [ ] Saw "Stage View" with 9 boxes
- [ ] All boxes are GREEN ✅

If all checkboxes pass → **Pipeline is fixed!** 🎉

---

## 📸 Screenshots You Should See

**Screenshot 1:** Configure page with Pipeline section visible

**Screenshot 2:** Stage View with all 9 stages (the green boxes)

**Screenshot 3:** Click on "Unit Tests" stage → shows test output:
```
===== 21 passed in X.XXs =====
Coverage: 80%+
```

**Screenshot 4:** Click on "Static Analysis" stage → shows:
```
=== Static Analysis Complete ===
Total errors: 0
```

These 4 screenshots are your proof! 📸

---

## 🚀 Last Resort: Rebuild from Scratch

If nothing works, delete the job and recreate it:

1. Jenkins → ml-autoscaling-pipeline → **Delete Pipeline**
2. Jenkins → **New Item**
3. Name: `ml-autoscaling-pipeline`
4. Type: **Pipeline**
5. Click OK
6. In "Definition" dropdown: Select **Pipeline script from SCM**
7. SCM: **Git**
   - Repository URL: `https://github.com/prerna3640/HA-K8S1.git`
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`
8. Click **Save**
9. Click **Build Now**

This will create completely fresh pipeline.

---

Good luck! Let me know which step you're on! 🎯
