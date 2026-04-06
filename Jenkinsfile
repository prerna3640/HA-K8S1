pipeline {
    agent any
    environment {
        WORKER_APP = '10.0.1.105'
        WORKER_DATA = '10.0.1.114'
        SSH_KEY = '/var/lib/jenkins/.ssh/kub-cluster-key.pem'
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/prerna3640/HA-K8S1.git'
            }
        }
        stage('Build ML Predictor') {
            steps {
                sh '''
                    cd ml-predictor
                    sudo /usr/local/bin/buildkitd &>/dev/null &
                    sleep 3
                    sudo nerdctl --namespace k8s.io build -t ml-predictor:${BUILD_NUMBER} .
                '''
            }
        }
        stage('Build Predictive Scaler') {
            steps {
                sh '''
                    cd predictive-scaler
                    sudo nerdctl --namespace k8s.io build -t predictive-scaler:${BUILD_NUMBER} .
                '''
            }
        }
        stage('Transfer to Workers') {
            steps {
                sh '''
                    sudo nerdctl --namespace k8s.io save -o /tmp/ml-predictor.tar ml-predictor:${BUILD_NUMBER}
                    sudo nerdctl --namespace k8s.io save -o /tmp/predictive-scaler.tar predictive-scaler:${BUILD_NUMBER}

                    sudo scp -i ${SSH_KEY} -o StrictHostKeyChecking=no /tmp/ml-predictor.tar ubuntu@${WORKER_DATA}:/tmp/
                    sudo ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ubuntu@${WORKER_DATA} "sudo ctr -n k8s.io images import /tmp/ml-predictor.tar"

                    sudo scp -i ${SSH_KEY} -o StrictHostKeyChecking=no /tmp/predictive-scaler.tar ubuntu@${WORKER_APP}:/tmp/
                    sudo ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ubuntu@${WORKER_APP} "sudo ctr -n k8s.io images import /tmp/predictive-scaler.tar"
                '''
            }
        }
        stage('Deploy') {
            steps {
                sh '''
                    kubectl set image deployment/ml-predictor -n monitoring ml-predictor=docker.io/library/ml-predictor:${BUILD_NUMBER}
                    kubectl set image deployment/predictive-scaler -n monitoring predictive-scaler=docker.io/library/predictive-scaler:${BUILD_NUMBER}
                    kubectl rollout status deployment/predictive-scaler -n monitoring --timeout=120s || true
                '''
            }
        }
        stage('Verify') {
            steps {
                sh '''
                    echo "=== Build #${BUILD_NUMBER} Deployed ==="
                    kubectl get pods -n monitoring | grep -E "predictor|scaler"
                    kubectl get pods -n myapp | grep web
                '''
            }
        }
    }
    post {
        success {
            sh 'curl -s "https://api.telegram.org/bot8665863838:AAGjjlvA-s7ygCEFZ-yPb2CYAoDvnPYuj4Q/sendMessage" -d "chat_id=1150673339" -d "text=Jenkins Build %23${BUILD_NUMBER} SUCCESS - Deployed to K8s"'
        }
        failure {
            sh 'curl -s "https://api.telegram.org/bot8665863838:AAGjjlvA-s7ygCEFZ-yPb2CYAoDvnPYuj4Q/sendMessage" -d "chat_id=1150673339" -d "text=Jenkins Build %23${BUILD_NUMBER} FAILED - Check console"'
        }
    }
}
