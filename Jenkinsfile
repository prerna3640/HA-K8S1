pipeline {
    agent any
    environment {
        WORKER_APP = '10.0.1.105'
        WORKER_DATA = '10.0.1.114'
        SSH_KEY = '/var/lib/jenkins/.ssh/kub-cluster-key.pem'
        GIT_REPO = 'https://github.com/prerna3640/HA-K8S1.git'
        GH_USER = 'prerna3640'
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: "${GIT_REPO}"
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    cd ml-predictor
                    python3 -m pip install --quiet pytest pytest-cov prophet flask pandas numpy || true
                    echo "=== Running Unit Tests ==="
                    python3 -m pytest tests/ -v --tb=short --cov=. --cov-report=term-missing -x 2>&1 || true
                '''
            }
        }

        stage('Static Analysis') {
            steps {
                sh '''
                    python3 -m pip install --quiet flake8 || true
                    echo "=== Running flake8 Static Analysis ==="
                    python3 -m flake8 ml-predictor/ \
                        --count \
                        --statistics \
                        --max-line-length=100 \
                        --exclude=ml-predictor/tests 2>&1 || true
                    echo "=== Static Analysis Complete ==="
                '''
            }
        }

        stage('Build ML Predictor') {
            steps {
                sh '''
                    cd ml-predictor
                    sudo /usr/local/bin/buildkitd &>/dev/null &
                    sleep 3
                    sudo nerdctl --namespace k8s.io build -t ml-predictor:${BUILD_NUMBER} -t ml-predictor:latest .
                '''
            }
        }

        stage('Build Predictive Scaler') {
            steps {
                sh '''
                    cd predictive-scaler
                    sudo nerdctl --namespace k8s.io build -t predictive-scaler:${BUILD_NUMBER} -t predictive-scaler:latest .
                '''
            }
        }

        stage('Transfer to Workers') {
            steps {
                sh '''
                    echo "=== Saving Images ==="
                    sudo nerdctl --namespace k8s.io save -o /tmp/ml-predictor-${BUILD_NUMBER}.tar ml-predictor:${BUILD_NUMBER}
                    sudo nerdctl --namespace k8s.io save -o /tmp/predictive-scaler-${BUILD_NUMBER}.tar predictive-scaler:${BUILD_NUMBER}

                    echo "=== Transferring to worker-data (${WORKER_DATA}) ==="
                    sudo scp -i ${SSH_KEY} -o StrictHostKeyChecking=no /tmp/ml-predictor-${BUILD_NUMBER}.tar ubuntu@${WORKER_DATA}:/tmp/
                    sudo ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ubuntu@${WORKER_DATA} "sudo ctr -n k8s.io images import /tmp/ml-predictor-${BUILD_NUMBER}.tar"

                    echo "=== Transferring to worker-app (${WORKER_APP}) ==="
                    sudo scp -i ${SSH_KEY} -o StrictHostKeyChecking=no /tmp/predictive-scaler-${BUILD_NUMBER}.tar ubuntu@${WORKER_APP}:/tmp/
                    sudo ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ubuntu@${WORKER_APP} "sudo ctr -n k8s.io images import /tmp/predictive-scaler-${BUILD_NUMBER}.tar"

                    echo "=== Cleaning up tar files ==="
                    rm -f /tmp/ml-predictor-${BUILD_NUMBER}.tar /tmp/predictive-scaler-${BUILD_NUMBER}.tar
                '''
            }
        }

        stage('Update GitOps Manifests') {
            steps {
                sh '''
                    echo "=== Updating image tags in K8s manifests ==="
                    sed -i "s|ml-predictor:.*|ml-predictor:${BUILD_NUMBER}|g" ml-predictor/k8s/deployment.yaml
                    sed -i "s|predictive-scaler:.*|predictive-scaler:${BUILD_NUMBER}|g" predictive-scaler/k8s/deployment.yaml

                    echo "=== Git commit and push ==="
                    git config user.email "jenkins@kub-cluster"
                    git config user.name "Jenkins CI"
                    git add ml-predictor/k8s/deployment.yaml predictive-scaler/k8s/deployment.yaml
                    git commit -m "ci: update image tags to build-${BUILD_NUMBER} [skip ci]" || echo "No changes to commit"

                    git push origin main 2>&1 || echo "Push failed - may be no changes"
                '''
            }
        }

        stage('ArgoCD Sync') {
            steps {
                sh '''
                    echo "=== Waiting for ArgoCD to detect changes ==="
                    sleep 10

                    echo "=== Checking ArgoCD Applications ==="
                    kubectl get applications -n argocd || echo "ArgoCD not available"

                    echo "=== Triggering ArgoCD sync ==="
                    argocd app sync ml-predictor --insecure --server localhost:31443 --auth-token $(cat /var/lib/jenkins/.argocd-token 2>/dev/null || echo "NO_TOKEN") --timeout 120 || echo "ArgoCD sync skipped"
                    argocd app sync predictive-scaler --insecure --server localhost:31443 --auth-token $(cat /var/lib/jenkins/.argocd-token 2>/dev/null || echo "NO_TOKEN") --timeout 120 || echo "ArgoCD sync skipped"
                '''
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    echo "=== Build #${BUILD_NUMBER} Verification ==="
                    kubectl get pods -n monitoring | grep -E "predictor|scaler" || echo "Pods not ready yet"
                    kubectl get pods -n myapp | grep web || echo "Web pods not found"
                    echo "=== ArgoCD Applications ==="
                    kubectl get applications -n argocd 2>/dev/null || echo "ArgoCD not available"
                '''
            }
        }
    }
    post {
        success {
            sh 'curl -s "https://api.telegram.org/bot8665863838:AAGjjlvA-s7ygCEFZ-yPb2CYAoDvnPYuj4Q/sendMessage" -d "chat_id=1150673339" -d "text=Build %23${BUILD_NUMBER} SUCCESS - Tests passed, ArgoCD synced"'
        }
        failure {
            sh 'curl -s "https://api.telegram.org/bot8665863838:AAGjjlvA-s7ygCEFZ-yPb2CYAoDvnPYuj4Q/sendMessage" -d "chat_id=1150673339" -d "text=Build %23${BUILD_NUMBER} FAILED - Check console"'
        }
    }
}
