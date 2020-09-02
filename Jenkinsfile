#!/usr/bin/env groovy
import java.io.File;
node('Jenkins-Backend-Slave') {
    timestamps {
      properties([
        buildDiscarder(logRotator(
          artifactDaysToKeepStr: '',
          artifactNumToKeepStr: '',
          daysToKeepStr: '60',
          numToKeepStr: '10'
        )),
        parameters([
          booleanParam(
            defaultValue: false,
            description: 'Check this box if you want to skip the test case execution for the current build', name: 'skipTestsFlag')
        ]),
        disableConcurrentBuilds()
      ])
      timeout(activity: true, time: 5) {
        stage('Code Checkout'){
          try{
            cleanWs()
            checkout([
              $class: 'GitSCM',
              branches: scm.branches,
              extensions: scm.extensions + [[$class: 'CleanCheckout']] +
              [[$class: 'LocalBranch', localBranch: "${env.BRANCH_NAME}" ]],
              userRemoteConfigs: scm.userRemoteConfigs
            ])
            withCredentials([
              [$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: 'is_devops_prod',
              accessKeyVariable: 'Dev_AWS_ACCESS_KEY_ID',
              secretKeyVariable: 'Dev_AWS_SECRET_ACCESS_KEY'
              ],
              [$class: 'AmazonWebServicesCredentialsBinding',
              credentialsId: 'ab1d6684-0bcf-4869-aed5-c22e607ba742',
              accessKeyVariable: 'Prod_AWS_ACCESS_KEY_ID',
              secretKeyVariable: 'Prod_AWS_SECRET_ACCESS_KEY'
              ]]){
                sh """
                  sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile devProfile
                  sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile devProfile
                  sudo aws configure set region us-east-1 --profile devProfile
                  sudo aws configure set aws_access_key_id ${env.Prod_AWS_ACCESS_KEY_ID} --profile prodProfile
                  sudo aws configure set aws_secret_access_key ${env.Prod_AWS_SECRET_ACCESS_KEY} --profile prodProfile
                  sudo aws configure set region us-east-1 --profile prodProfile
                  sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile default
                  sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile default
                  sudo aws configure set region us-east-1 --profile default
                """
              }
          }
          catch(e){
            echo "Code Checkout has failed : ${e}"
            Notify()
            throw(e)
          }
        }

        stage('Verify Parameters'){
          withCredentials([usernamePassword(credentialsId: 'is_cicd_github', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USER')]){
          sh """
            export PYTHONPATH=${env.WORKSPACE}
            sudo chown -R ubuntu:ubuntu ~/.aws
            python3 parameters/freeze_ssm_params.py --profile devProfile
            python3 parameters/freeze_ssm_params.py --profile prodProfile
            git diff > /tmp/diff.txt
            sudo chown -R ubuntu:ubuntu ~/.gitconfig
            cat /tmp/diff.txt
            if [ -s "/tmp/diff.txt" ]
            then
                echo "Some of the parameters have changed hence commiting them and aborting the build"
                git config --global credential.username ${env.GIT_USER}
                git config --global credential.email monitoring@iterativescopes.com
                git config --global credential.helper "!echo password=${env.GIT_PASSWORD}; echo"
                git add parameters/ || true
                git commit -m "Updated the latest ssm parameter values for both the accounts" || true
                git reset --hard HEAD || true
                git pull origin ${env.BRANCH_NAME} || true
                git push origin ${env.BRANCH_NAME} || true
            else
                echo "Continuing with the build as there are no changes"
                rm /tmp/diff.txt
            fi
          """
          }
        }

        stage('Setup Python Venv'){
          withCredentials([
            file(credentialsId: 'is_docker.pem',
            variable: 'ssh_key')]){
            sh """
                touch ~/.ssh/is_docker.pem
                chmod 600 ~/.ssh/is_docker.pem
                cat ${env.ssh_key} > ~/.ssh/is_docker.pem
                sudo chown ubuntu:ubuntu ~/.ssh/is_docker.pem
                ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts
                if [ ! -d "venv" ]; then
                        python3 -m venv venv --system-site-packages
                fi
                . venv/bin/activate
                pip install wheel==0.34.2
                pip install -r requirements-dev.txt
            """
            }
        }
        if (!fileExists('/tmp/diff.txt')){
            stage('Unit Tests'){
              if(!params.skipTestsFlag){
                try{
                  sh '''
                    echo Running unit tests
                    . venv/bin/activate
                    # make sure pg is ready to accept connections
                    until pg_isready -h localhost -p 5432 -U postgres
                    do
                      echo "Waiting for postgres at"
                      sleep 2;
                    done
                    # Now able to connect to postgres
                    export FFPROBE_BINARY=/snap/bin/ffprobe
                    export FFMPEG_BINARY=/snap/bin/ffmpeg
                    export PATH=$PATH:/usr/bin/mysql
                    pip install sklearn;
                    python3 -m pytest labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests casemaker/api_services/tests casemaker/data_services/tests casemaker/sqs_jobs/tests --junitxml=test_report.xml
                  '''
                }
                catch(e){
                  echo "Unit tests have failed : ${e}"
                  Notify()
                  throw(e)
                }
                finally{
                  echo "Publishing test result report"
                  junit allowEmptyResults: true, testResults: 'test_report.xml'
                }
              }
            }

            stage('Pylint'){
              if(!params.skipTestsFlag){
                try{
                  sh"""
                    export FFPROBE_BINARY=/snap/bin/ffprobe
                    export FFMPEG_BINARY=/snap/bin/ffmpeg
                    find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests -name "*.pyc" -delete
                    find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests -name "*.coverage" -delete
                  """
                  sh '''
                    . venv/bin/activate
                    export TERM="linux"
                    export FFPROBE_BINARY=/snap/bin/ffprobe
                    export FFMPEG_BINARY=/snap/bin/ffmpeg
                    python3 -m coverage run -m  pytest $(find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests casemaker/api_services/tests casemaker/data_services/tests casemaker/sqs_jobs/tests -name "test*.py" -print) || true
                    coverage report -m $(find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests casemaker/api_services/tests casemaker/data_services/tests casemaker/sqs_jobs/tests -name "test*.py" -print | awk '{split($0,a,"tests/test_"); print a[1]a[2], a[2];}' | awk '{split($0,a,"."); print a[1]"/"$2;}') || true
                    coverage xml -i $(find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests casemaker/api_services/tests casemaker/data_services/tests casemaker/sqs_jobs/tests -name "test*.py" -print | awk '{split($0,a,"tests/test_"); print a[1]a[2], a[2];}' | awk '{split($0,a,"."); print a[1]"/"$2;}') || true
                    coverage html -i $(find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests casemaker/api_services/tests casemaker/data_services/tests casemaker/sqs_jobs/tests -name "test*.py" -print | awk '{split($0,a,"tests/test_"); print a[1]a[2], a[2];}' | awk '{split($0,a,"."); print a[1]"/"$2;}') || true
                    pylint --rcfile=pylint.cfg $(find labelmaker/api_services/tests labelmaker/data_services/tests labelmaker/sqs_jobs/tests casemaker/api_services/tests casemaker/data_services/tests casemaker/sqs_jobs/tests -name "test*.py" -print) MYMODULE/ > pylint.log || exit 0
                  '''
                }
                catch(e){
                  echo "Pylint has failed : ${e}"
                  Notify()
                  throw(e)
                }
              }
            }

            stage('Deploy Lambda Layers'){
              try{
                dir('deploy_layer'){
                  withCredentials([
                    file(credentialsId: 'is_docker.pem',
                    variable: 'ssh_key')]){
                    bulk_copy(copy_list)
                    sh """
                      sudo chown -R ubuntu:ubuntu ~/.aws
                      sudo chown -R ubuntu:ubuntu ~/.npm
                      sudo chown -R ubuntu:ubuntu ~/.config
                      sudo snap install docker
                      sudo chown -R ubuntu:ubuntu ${env.WORKSPACE}/deploy_layer/ ${env.WORKSPACE}/casemaker/sqs_jobs/
                      cd ${env.WORKSPACE}
                      export PATH=$PATH:/snap/bin
                      sudo chmod 777 /var/run/docker.sock || true
                    """
                    env_build(env_list)
                    }
                }
              }
              catch(e){
                echo "Lambda layer build has failed : ${e}"
                Notify()
                throw(e)
              }
            }

            stage('Build Artifacts'){
              try{
                dir('labelmaker'){
                  withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: 'is_devops_prod',
                    accessKeyVariable: 'Dev_AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'Dev_AWS_SECRET_ACCESS_KEY'
                    ],
                    [$class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: 'ab1d6684-0bcf-4869-aed5-c22e607ba742',
                    accessKeyVariable: 'Prod_AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'Prod_AWS_SECRET_ACCESS_KEY'
                    ]]){
                      sh """
                        sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile default
                        sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile default
                        sudo aws configure set region us-east-1 --profile default
                        sudo chown -R ubuntu:ubuntu ~/.aws
                        sudo chown -R ubuntu:ubuntu ~/.npm
                        sudo chown -R ubuntu:ubuntu ~/.config

                        #Package labelmaker serverless artifacts
                        cd ${env.WORKSPACE}/core-backend-dev/labelmaker
                        sls package --alias dev --stage dev --package ${env.WORKSPACE}/labelmaker/build_artifacts_dev
                        sudo sync; sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"

                        cd ${env.WORKSPACE}/core-backend-qa/labelmaker
                        sls package --alias qa --stage qa --package ${env.WORKSPACE}/labelmaker/build_artifacts_qa
                        sudo sync; sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"

                        cd ${env.WORKSPACE}/core-backend-stage/labelmaker
                        sls package --alias stage --stage stage --package ${env.WORKSPACE}/labelmaker/build_artifacts_stage
                        sudo sync; sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"

                        cd ${env.WORKSPACE}/core-backend-prod/labelmaker
                        sls package --alias prod --stage prod --package ${env.WORKSPACE}/labelmaker/build_artifacts_prod
                        #Package casemaker serverless artifacts
                        cd ${env.WORKSPACE}/core-backend-dev/casemaker

                        sls package --alias dev --stack dev --package ${env.WORKSPACE}/casemaker/casemaker_build_artifacts_dev
                        sudo sync; sudo sh -c "echo 3 > /proc/sys/vm/drop_caches"

                        cd ${env.WORKSPACE}/labelmaker/
                        sed -i 's;${env.WORKSPACE};/home/ubuntu/workspace/DeployLabelmaker;' build_artifacts_dev/serverless-state.json
                        sed -i 's;core-backend-dev/labelmaker;labelmaker;' build_artifacts_dev/serverless-state.json

                        sed -i 's;${env.WORKSPACE};/home/ubuntu/workspace/DeployLabelmaker;' build_artifacts_qa/serverless-state.json
                        sed -i 's;core-backend-qa/labelmaker;labelmaker;' build_artifacts_qa/serverless-state.json

                        sed -i 's;${env.WORKSPACE};/home/ubuntu/workspace/DeployLabelmaker;' build_artifacts_stage/serverless-state.json
                        sed -i 's;core-backend-stage/labelmaker;labelmaker;' build_artifacts_stage/serverless-state.json

                        sed -i 's;${env.WORKSPACE};/home/ubuntu/workspace/DeployLabelmaker;' build_artifacts_prod/serverless-state.json
                        sed -i 's;core-backend-prod/labelmaker;labelmaker;' build_artifacts_prod/serverless-state.json

                        zip -r sls_dev.zip build_artifacts_dev
                        zip -r sls_qa.zip build_artifacts_qa
                        zip -r sls_stage.zip build_artifacts_stage
                        zip -r sls_prod.zip build_artifacts_prod

                        cd ${env.WORKSPACE}/casemaker/
                        sed -i 's;${env.WORKSPACE};/home/ubuntu/workspace/DeployCasemaker;' casemaker_build_artifacts_dev/serverless-state.json
                        sed -i 's;core-backend-dev/casemaker;casemaker;' casemaker_build_artifacts_dev/serverless-state.json
                        zip -r sls_casemaker_dev.zip casemaker_build_artifacts_dev
                      """
                  }
                }
                sh """
                  #package Downsampling and Decomposition artifacts
                  zip -r video_decomposition.zip "labelmaker/data_services/video_decomposition/video_decomposition.py" "labelmaker/data_services/video_decomposition/status.py" "labelmaker/data_services/video_decomposition/VideoDecompositionJob.py" "labelmaker/data_services/video_decomposition/create_env.sh" "utils.py" "core_services"
                  zip -r video_downsampling.zip "labelmaker/data_services/video_downsampling/video_downsampling.py" "labelmaker/data_services/video_downsampling/status.py" "labelmaker/data_services/video_downsampling/create_env.sh" "utils.py" "core_services"
                """
              }
              catch(e){
                echo "Build artifacts has failed : ${e}"
                Notify()
                throw(e)
              }
            }

            stage('Generate Test Report'){
              if(!params.skipTestsFlag){
                try{
                  cobertura autoUpdateHealth: false,
                  autoUpdateStability: false,
                  coberturaReportFile: 'coverage.xml',
                  conditionalCoverageTargets: '70, 0, 0',
                  failUnhealthy: false,
                  failUnstable: false,
                  lineCoverageTargets: '80, 0, 0',
                  maxNumberOfBuilds: 0,
                  methodCoverageTargets: '80, 0, 0',
                  onlyStable: false,
                  sourceEncoding: 'ASCII',
                  zoomCoverageChart: false
                }
                catch(e){
                  echo "Test Report generation has failed : ${e}"
                  Notify()
                  throw(e)
                }
              }
            }
            stage('Publish HTML Reports') {
              if(!params.skipTestsFlag){
                try{
                  publishHTML([allowMissing: true, alwaysLinkToLastBuild: true, keepAll: true, reportDir: 'htmlcov', reportFiles: 'index.html', reportName: 'HTML Report', reportTitles: ''])
                }
                catch(e){
                  echo "HTML Report generation has failed : ${e}"
                  Notify()
                  throw(e)
                }
              }
            }
            stage('Publish Warnings'){
              if(!params.skipTestsFlag){
                try {
                  scanForIssues tool: pyLint(pattern: 'pylint.log')
                  recordIssues(tools: [pyLint(pattern: 'pylint.log')])
                }
                catch(e){
                  echo "Publish Warnings has failed : ${e}"
                  Notify()
                  throw(e)
                }
              }
            }
            stage('Publish Artifacts'){
              try{
                step([
                  $class: 'S3BucketPublisher',
                  dontWaitForConcurrentBuildCompletion: false,
                  entries: [[
                    bucket: 'is-jenkins-artifacts',
                    excludedFile: '',
                    flatten: false,
                    gzipFiles: false,
                    keepForever: false,
                    managedArtifacts: true,
                    noUploadOnFailure: true,
                    selectedRegion: 'us-east-1',
                    sourceFile: 'video_decomposition.zip,video_downsampling.zip,labelmaker/sls_*.zip,casemaker/sls_*.zip,*-python.zip',
                    storageClass: 'STANDARD',
                    uploadFromSlave: true,
                    useServerSideEncryption: false
                  ]],
                  profileName: 'Builds',
                  userMetadata: []
                ])
              }
              catch(e){
                echo "Publish Artifacts has failed : ${e}"
                Notify()
                throw(e)
              }
            }

            stage('Publish ECR Images'){
              try{
                dir('casemaker/sqs_jobs'){
                  withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: 'is_devops_prod',
                    accessKeyVariable: 'Dev_AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'Dev_AWS_SECRET_ACCESS_KEY'
                    ],
                    [$class: 'AmazonWebServicesCredentialsBinding',
                    credentialsId: 'ab1d6684-0bcf-4869-aed5-c22e607ba742',
                    accessKeyVariable: 'Prod_AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'Prod_AWS_SECRET_ACCESS_KEY'
                    ]]){
                      sh """
                        sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile devProfile
                        sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile devProfile
                        sudo aws configure set region us-east-1 --profile devProfile

                        sudo aws configure set aws_access_key_id ${env.Prod_AWS_ACCESS_KEY_ID} --profile prodProfile
                        sudo aws configure set aws_secret_access_key ${env.Prod_AWS_SECRET_ACCESS_KEY} --profile prodProfile
                        sudo aws configure set region us-east-1 --profile prodProfile

                        sudo aws configure set aws_access_key_id ${env.Dev_AWS_ACCESS_KEY_ID} --profile default
                        sudo aws configure set aws_secret_access_key ${env.Dev_AWS_SECRET_ACCESS_KEY} --profile default
                        sudo aws configure set region us-east-1 --profile default

                        sudo chown -R ubuntu:ubuntu ~/.aws
                        sudo chown -R ubuntu:ubuntu ~/.npm
                        sudo chown -R ubuntu:ubuntu ~/.config

                        sudo chmod 777 /var/run/docker.sock || true
                        rsync -r ${env.WORKSPACE}/casemaker ${env.WORKSPACE}/casemaker/sqs_jobs/case_extraction/
                        rsync -r ${env.WORKSPACE}/labelmaker ${env.WORKSPACE}/casemaker/sqs_jobs/case_extraction/
                        cp -r ${env.WORKSPACE}/casemaker/sqs_jobs/case_extraction/casemaker ${env.WORKSPACE}/casemaker/sqs_jobs/procedure_detection/
                        cp -r ${env.WORKSPACE}/casemaker/sqs_jobs/case_extraction/casemaker ${env.WORKSPACE}/casemaker/sqs_jobs/redaction/
                        cp -r ${env.WORKSPACE}/casemaker/sqs_jobs/case_extraction/labelmaker ${env.WORKSPACE}/casemaker/sqs_jobs/procedure_detection/
                        cp -r ${env.WORKSPACE}/casemaker/sqs_jobs/case_extraction/labelmaker ${env.WORKSPACE}/casemaker/sqs_jobs/redaction/
                      """

                      ecr_login = sh(script: "/bin/bash -c \'aws ecr get-login-password --region us-east-1 | /snap/bin/docker login --username AWS --password-stdin 691195436300.dkr.ecr.us-east-1.amazonaws.com/case_extraction\'", returnStdout: true)
                      echo ecr_login
                      dir('case_extraction'){
                          sh """
                            #Package casemaker images
                            /snap/bin/docker build -f CE_Dockerfile --build-arg SSH_KEY=is_docker.pem --build-arg LINUX_USER=is-docker -t case_extraction:${env.BRANCH_NAME} .
                            /snap/bin/docker tag case_extraction:${env.BRANCH_NAME} 691195436300.dkr.ecr.us-east-1.amazonaws.com/case_extraction:${env.BRANCH_NAME}
                            /snap/bin/docker push 691195436300.dkr.ecr.us-east-1.amazonaws.com/case_extraction:${env.BRANCH_NAME}
                          """
                      }
                      dir('procedure_detection'){
                          sh """
                            #Package casemaker images
                            /snap/bin/docker build -f PD_Dockerfile --build-arg SSH_KEY=is_docker.pem --build-arg LINUX_USER=is-docker -t procedure_detection:${env.BRANCH_NAME} .
                            /snap/bin/docker tag procedure_detection:${env.BRANCH_NAME} 691195436300.dkr.ecr.us-east-1.amazonaws.com/procedure_detection:${env.BRANCH_NAME}
                            /snap/bin/docker push 691195436300.dkr.ecr.us-east-1.amazonaws.com/procedure_detection:${env.BRANCH_NAME}
                          """
                      }
                      dir('redaction'){
                          sh """
                            #Package casemaker images
                            /snap/bin/docker build -f RD_Dockerfile --build-arg SSH_KEY=is_docker.pem --build-arg LINUX_USER=is-docker -t redaction:${env.BRANCH_NAME} .
                            /snap/bin/docker tag redaction:${env.BRANCH_NAME} 691195436300.dkr.ecr.us-east-1.amazonaws.com/redaction:${env.BRANCH_NAME}
                            /snap/bin/docker push 691195436300.dkr.ecr.us-east-1.amazonaws.com/redaction:${env.BRANCH_NAME}
                          """
                      }
                  }
                }
              }
              catch(e){
                echo "ECR Image creation has failed : ${e}"
                Notify()
                throw(e)
              }
            }
        }
      }
    }
}
def Notify(){
  emailext body: "Please check ${env.BUILD_URL} for more details on this",
           recipientProviders: [culprits()],
           subject: "Core Backend build has failed for ${env.BRANCH_NAME} branch"
}

def bulk_copy(list) {
    sh "echo Going to echo a list"
    for (int i = 0; i < list.size(); i++) {
        sh """mkdir -p ${env.WORKSPACE}/${list[i]}
              touch ${env.WORKSPACE}/${list[i]}/is_docker.pem
              cat ${env.ssh_key} | tee -a ${env.WORKSPACE}/${list[i]}/is_docker.pem > /dev/null
              cp -r ${env.WORKSPACE}/core_services ${env.WORKSPACE}/${list[i]}/
        """
    }
}

def env_build(env_list) {
  sh """
        #Deploying lambda layer for all the environments and applications
  """
  for (int i = 0; i < env_list.size(); i++) {
      sh """
        cd ${env.WORKSPACE}
        export PATH=$PATH:/snap/bin
        sudo chmod 777 /var/run/docker.sock || true
        ./deploy-app-layer.sh --app labelmaker --env ${env_list[i]} --alias ${env_list[i]};
        ./deploy-python-layer.sh --app labelmaker --env ${env_list[i]} --alias ${env_list[i]} --ssh-key ${env.ssh_key};
      """
  }
}
