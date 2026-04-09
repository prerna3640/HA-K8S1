# Fix Jenkins Pipeline - Reload Jenkinsfile

Your Jenkinsfile has been **updated with 9 stages** (Unit Tests, Static Analysis, etc.), but Jenkins is still showing the **old pipeline with fewer stages**.

This happens because **Jenkins caches the pipeline definition** and needs to reload it from GitHub.

---

## 🔧 Manual Fix (via Jenkins UI)

### Step 1: Open Jenkins
- Go to: **http://<master-public-ip>:8080**
- Login with your credentials

### Step 2: Select the Job
- Click on **ml-autoscaling-pipeline** (or **HA-K8S1** if that's the job name)

### Step 3: Click Configure
- Left sidebar → **Configure**
- OR top menu → **Configure**

### Step 4: Update Pipeline Configuration

Look for the **Pipeline** section (usually at bottom). You should see:

```
Pipeline script from SCM
- SCM: Git
- Repository URL: https://github.com/prerna3640/HA-K8S1.git
- Branch: */main
- Script Path: Jenkinsfile
```

**Make sure these are correct:**
- ✅ Repository URL = `https://github.com/prerna3640/HA-K8S1.git`
- ✅ Branch = `*/main`
- ✅ Script Path = `Jenkinsfile`

### Step 5: Save & Rebuild
- Click **Save** (bottom of page)
- Jenkins will now fetch fresh Jenkinsfile from GitHub
- Click **Build Now** to trigger a new build
- The new build (#3 or #4) will show **9 stages**

---

## Expected Output After Fix

Your pipeline will show **these 9 stages:**

1. ✅ **Checkout** (git clone)
2. ✅ **Unit Tests** (pytest with coverage) **← NEW**
3. ✅ **Static Analysis** (flake8) **← NEW**
4. ✅ **Build ML Predictor** (nerdctl build)
5. ✅ **Build Predictive Scaler** (nerdctl build)
6. ✅ **Transfer to Workers** (scp + import)
7. ✅ **Update GitOps Manifests** (sed + git push)
8. ✅ **ArgoCD Sync** (automatic deployment)
9. ✅ **Verify** (kubectl check)

---

## If Manual Fix Doesn't Work

Try this **via Jenkins Script Console**:

### Open Jenkins Script Console
1. Go to http://<master-public-ip>:8080
2. Click **Manage Jenkins** (left menu)
3. Click **Script Console**
4. Paste this code:

```groovy
Jenkins.instance.reload()
println "✓ Jenkins reloaded successfully"
```

5. Click **Run**
6. Wait 10-15 seconds for Jenkins to reload
7. Trigger a new build

---

## Verify New Stages Are Present

After rebuilding:

1. Open the new build (#3, #4, etc.)
2. Look at **Stage View**
3. You should see green boxes for all 9 stages:
   - Checkout
   - Unit Tests ✓ (NEW)
   - Static Analysis ✓ (NEW)
   - Build ML Predictor
   - Build Predictive Scaler
   - Transfer to Workers
   - Update GitOps Manifests
   - ArgoCD Sync
   - Verify

---

## Troubleshooting

**Q: Still showing old stages?**
- Clear Jenkins cache: Go to job → Configure → Save (don't change anything)
- Trigger another build
- Check full console output to see if Jenkinsfile is being read from correct branch

**Q: Getting authentication errors?**
- Make sure you're logged in as a user with "Build" permission
- Contact Jenkins admin or check job permissions

**Q: Pipeline not executing?**
- Check Jenkins has:
  - ✅ Git plugin installed
  - ✅ Pipeline plugin installed
  - ✅ SSH key for workers configured
  - ✅ Docker/nerdctl available

---

## What Changed in Jenkinsfile

Compare with commit: `e13686f` (feat: add end-to-end DevOps pipeline...)

**New Stages Added:**
```groovy
stage('Unit Tests') {
    steps {
        sh '''
            cd ml-predictor
            python3 -m pytest tests/ -v --cov=. --cov-report=term-missing
        '''
    }
}

stage('Static Analysis') {
    steps {
        sh '''
            python3 -m flake8 ml-predictor/ --count --statistics
        '''
    }
}
```

**New Stage (Update Manifests):**
```groovy
stage('Update GitOps Manifests') {
    steps {
        sh '''
            sed -i "s|ml-predictor:.*|ml-predictor:${BUILD_NUMBER}|g" ml-predictor/k8s/deployment.yaml
            git config user.email "jenkins@kub-cluster"
            git config user.name "Jenkins CI"
            git add ml-predictor/k8s/deployment.yaml
            git commit -m "ci: update image tags to build-${BUILD_NUMBER}" || true
            git push origin main
        '''
    }
}
```

**New Stage (ArgoCD Sync):**
```groovy
stage('ArgoCD Sync') {
    steps {
        sh '''
            argocd app sync ml-predictor --server localhost:31443
        '''
    }
}
```

---

## Summary

✅ Jenkinsfile updated with new stages  
✅ Pushed to GitHub (branch: main)  
❌ Jenkins needs to reload the Jenkinsfile  

**Next Step:** Follow the manual fix steps above to reload Jenkins pipeline.

After that, your teacher will see:
- ✅ Unit tests running
- ✅ Code quality checks
- ✅ Automatic ArgoCD sync
- ✅ Full end-to-end DevOps pipeline!

---

Good luck! Let me know if you need help with any step. 🚀
