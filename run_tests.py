#!/usr/bin/env python3
"""
テスト実行スクリプト
全てのテストを実行し、結果をレポートとして出力する
"""
import subprocess
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path
import argparse


class TestRunner:
    """テスト実行クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_dir = self.project_root / "backend"
        self.frontend_dir = self.project_root / "frontend"
        self.results = {}
        
    def run_command(self, command, cwd=None, timeout=300):
        """コマンドを実行し、結果を返す"""
        try:
            start_time = time.time()
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            end_time = time.time()
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'duration': end_time - start_time
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'returncode': -1,
                'duration': timeout
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'duration': 0
            }
    
    def setup_backend_environment(self):
        """バックエンド環境のセットアップ"""
        print("Setting up backend test environment...")
        
        # 仮想環境の確認
        venv_path = self.project_root / "venv"
        if not venv_path.exists():
            print("Creating virtual environment...")
            result = self.run_command("python -m venv venv")
            if not result['success']:
                print(f"Failed to create virtual environment: {result['stderr']}")
                return False
        
        # 依存関係のインストール
        pip_cmd = str(venv_path / "Scripts" / "pip.exe") if os.name == 'nt' else str(venv_path / "bin" / "pip")
        requirements_file = self.backend_dir / "requirements.txt"
        
        if requirements_file.exists():
            print("Installing backend dependencies...")
            result = self.run_command(f"{pip_cmd} install -r {requirements_file}")
            if not result['success']:
                print(f"Failed to install dependencies: {result['stderr']}")
                return False
        
        # テスト用依存関係のインストール
        test_packages = [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "psutil>=5.9.0"
        ]
        
        print("Installing test dependencies...")
        for package in test_packages:
            result = self.run_command(f"{pip_cmd} install {package}")
            if not result['success']:
                print(f"Warning: Failed to install {package}")
        
        return True
    
    def setup_frontend_environment(self):
        """フロントエンド環境のセットアップ"""
        print("Setting up frontend test environment...")
        
        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            print("Warning: package.json not found in frontend directory")
            return False
        
        # Node.js依存関係のインストール
        print("Installing frontend dependencies...")
        result = self.run_command("npm install", cwd=self.frontend_dir)
        if not result['success']:
            print(f"Failed to install frontend dependencies: {result['stderr']}")
            return False
        
        # Playwright のインストール
        print("Installing Playwright browsers...")
        result = self.run_command("npx playwright install", cwd=self.frontend_dir)
        if not result['success']:
            print(f"Warning: Failed to install Playwright browsers: {result['stderr']}")
        
        return True
    
    def run_backend_tests(self, test_type="all"):
        """バックエンドテストの実行"""
        print(f"Running backend tests ({test_type})...")
        
        # Pythonの実行パスを取得
        venv_path = self.project_root / "venv"
        python_cmd = str(venv_path / "Scripts" / "python.exe") if os.name == 'nt' else str(venv_path / "bin" / "python")
        
        test_commands = {
            "unit": f"{python_cmd} -m pytest backend/tests/test_core backend/tests/test_ml backend/tests/test_monitoring -v --cov=backend --cov-report=html --cov-report=xml",
            "integration": f"{python_cmd} -m pytest backend/tests/test_api -v --cov=backend --cov-report=html --cov-report=xml",
            "performance": f"{python_cmd} -m pytest backend/tests/test_performance.py -v --tb=short",
            "all": f"{python_cmd} -m pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=xml --cov-report=term"
        }
        
        command = test_commands.get(test_type, test_commands["all"])
        result = self.run_command(command, cwd=self.project_root, timeout=600)
        
        self.results['backend'] = {
            'type': test_type,
            'success': result['success'],
            'duration': result['duration'],
            'output': result['stdout'],
            'errors': result['stderr']
        }
        
        return result['success']
    
    def run_frontend_tests(self, test_type="all"):
        """フロントエンドテストの実行"""
        print(f"Running frontend tests ({test_type})...")
        
        test_commands = {
            "unit": "npm run test -- --coverage --watchAll=false",
            "e2e": "npx playwright test",
            "performance": "npx playwright test e2e/performance.spec.ts",
            "all": "npm run test:all"
        }
        
        # package.jsonにtest:allスクリプトが存在しない場合の対応
        if test_type == "all":
            # 単体テストとE2Eテストを順次実行
            unit_result = self.run_command(test_commands["unit"], cwd=self.frontend_dir, timeout=300)
            e2e_result = self.run_command(test_commands["e2e"], cwd=self.frontend_dir, timeout=600)
            
            success = unit_result['success'] and e2e_result['success']
            duration = unit_result['duration'] + e2e_result['duration']
            output = f"Unit Tests:\n{unit_result['stdout']}\n\nE2E Tests:\n{e2e_result['stdout']}"
            errors = f"Unit Test Errors:\n{unit_result['stderr']}\n\nE2E Test Errors:\n{e2e_result['stderr']}"
        else:
            command = test_commands.get(test_type, test_commands["unit"])
            result = self.run_command(command, cwd=self.frontend_dir, timeout=600)
            success = result['success']
            duration = result['duration']
            output = result['stdout']
            errors = result['stderr']
        
        self.results['frontend'] = {
            'type': test_type,
            'success': success,
            'duration': duration,
            'output': output,
            'errors': errors
        }
        
        return success
    
    def check_test_coverage(self):
        """テストカバレッジの確認"""
        print("Checking test coverage...")
        
        coverage_results = {}
        
        # バックエンドカバレッジ
        coverage_xml = self.project_root / "coverage.xml"
        if coverage_xml.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(coverage_xml)
                root = tree.getroot()
                
                line_rate = float(root.get('line-rate', 0)) * 100
                branch_rate = float(root.get('branch-rate', 0)) * 100
                
                coverage_results['backend'] = {
                    'line_coverage': line_rate,
                    'branch_coverage': branch_rate
                }
            except Exception as e:
                print(f"Failed to parse backend coverage: {e}")
        
        # フロントエンドカバレッジ
        frontend_coverage = self.frontend_dir / "coverage" / "lcov-report" / "index.html"
        if frontend_coverage.exists():
            coverage_results['frontend'] = {
                'report_available': True,
                'report_path': str(frontend_coverage)
            }
        
        self.results['coverage'] = coverage_results
        return coverage_results
    
    def generate_test_report(self):
        """テスト結果レポートの生成"""
        print("Generating test report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_duration': sum([
                    self.results.get('backend', {}).get('duration', 0),
                    self.results.get('frontend', {}).get('duration', 0)
                ]),
                'backend_success': self.results.get('backend', {}).get('success', False),
                'frontend_success': self.results.get('frontend', {}).get('success', False)
            },
            'details': self.results
        }
        
        # JSONレポートの保存
        report_file = self.project_root / "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # HTMLレポートの生成
        html_report = self.generate_html_report(report)
        html_file = self.project_root / "test_report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        print(f"Test report saved to: {report_file}")
        print(f"HTML report saved to: {html_file}")
        
        return report
    
    def generate_html_report(self, report):
        """HTMLレポートの生成"""
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX Trading System - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .test-section {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .duration {{ color: #666; }}
        pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        .coverage {{ background-color: #e8f4f8; padding: 10px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FX Trading System - Test Report</h1>
        <p>Generated: {report['timestamp']}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Duration: <span class="duration">{report['summary']['total_duration']:.2f} seconds</span></p>
        <p>Backend Tests: <span class="{'success' if report['summary']['backend_success'] else 'failure'}">
            {'PASSED' if report['summary']['backend_success'] else 'FAILED'}
        </span></p>
        <p>Frontend Tests: <span class="{'success' if report['summary']['frontend_success'] else 'failure'}">
            {'PASSED' if report['summary']['frontend_success'] else 'FAILED'}
        </span></p>
    </div>
        """
        
        # バックエンドテスト結果
        if 'backend' in report['details']:
            backend = report['details']['backend']
            html += f"""
    <div class="test-section">
        <h2>Backend Tests ({backend['type']})</h2>
        <p>Status: <span class="{'success' if backend['success'] else 'failure'}">
            {'PASSED' if backend['success'] else 'FAILED'}
        </span></p>
        <p>Duration: <span class="duration">{backend['duration']:.2f} seconds</span></p>
        
        <h3>Output</h3>
        <pre>{backend['output'][:2000]}{'...' if len(backend['output']) > 2000 else ''}</pre>
        
        {f'<h3>Errors</h3><pre>{backend["errors"]}</pre>' if backend['errors'] else ''}
    </div>
            """
        
        # フロントエンドテスト結果
        if 'frontend' in report['details']:
            frontend = report['details']['frontend']
            html += f"""
    <div class="test-section">
        <h2>Frontend Tests ({frontend['type']})</h2>
        <p>Status: <span class="{'success' if frontend['success'] else 'failure'}">
            {'PASSED' if frontend['success'] else 'FAILED'}
        </span></p>
        <p>Duration: <span class="duration">{frontend['duration']:.2f} seconds</span></p>
        
        <h3>Output</h3>
        <pre>{frontend['output'][:2000]}{'...' if len(frontend['output']) > 2000 else ''}</pre>
        
        {f'<h3>Errors</h3><pre>{frontend["errors"]}</pre>' if frontend['errors'] else ''}
    </div>
            """
        
        # カバレッジ情報
        if 'coverage' in report['details']:
            coverage = report['details']['coverage']
            html += """
    <div class="test-section coverage">
        <h2>Test Coverage</h2>
            """
            
            if 'backend' in coverage:
                backend_cov = coverage['backend']
                html += f"""
        <h3>Backend Coverage</h3>
        <p>Line Coverage: {backend_cov.get('line_coverage', 0):.1f}%</p>
        <p>Branch Coverage: {backend_cov.get('branch_coverage', 0):.1f}%</p>
                """
            
            if 'frontend' in coverage:
                frontend_cov = coverage['frontend']
                html += f"""
        <h3>Frontend Coverage</h3>
        <p>Coverage report available: {frontend_cov.get('report_available', False)}</p>
        {f'<p>Report path: {frontend_cov.get("report_path", "")}</p>' if frontend_cov.get('report_path') else ''}
                """
            
            html += """
    </div>
            """
        
        html += """
</body>
</html>
        """
        
        return html
    
    def run_all_tests(self, backend_type="all", frontend_type="all", skip_setup=False):
        """全てのテストを実行"""
        print("=== FX Trading System - Test Runner ===")
        print(f"Backend test type: {backend_type}")
        print(f"Frontend test type: {frontend_type}")
        print()
        
        success = True
        
        # 環境セットアップ
        if not skip_setup:
            if not self.setup_backend_environment():
                print("Backend environment setup failed")
                success = False
            
            if not self.setup_frontend_environment():
                print("Frontend environment setup failed")
                success = False
        
        # バックエンドテスト実行
        if not self.run_backend_tests(backend_type):
            print("Backend tests failed")
            success = False
        
        # フロントエンドテスト実行
        if not self.run_frontend_tests(frontend_type):
            print("Frontend tests failed")
            success = False
        
        # カバレッジ確認
        self.check_test_coverage()
        
        # レポート生成
        report = self.generate_test_report()
        
        print("\n=== Test Execution Complete ===")
        print(f"Overall Success: {success}")
        print(f"Total Duration: {report['summary']['total_duration']:.2f} seconds")
        
        return success


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="FX Trading System Test Runner")
    parser.add_argument("--backend", choices=["unit", "integration", "performance", "all"], 
                       default="all", help="Backend test type")
    parser.add_argument("--frontend", choices=["unit", "e2e", "performance", "all"], 
                       default="all", help="Frontend test type")
    parser.add_argument("--skip-setup", action="store_true", 
                       help="Skip environment setup")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    success = runner.run_all_tests(args.backend, args.frontend, args.skip_setup)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()