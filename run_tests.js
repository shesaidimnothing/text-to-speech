const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
    gray: '\x1b[90m'
};

function colorize(text, color) {
    return `${color}${text}${colors.reset}`;
}

function parsePytestOutput(output) {
    const lines = output.split('\n');
    const results = {
        passed: [],
        failed: [],
        total: 0,
        passedCount: 0,
        failedCount: 0,
        duration: null
    };

    const testMap = new Map();

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmedLine = line.trim();

        const testMatch = line.match(/(test_\w+\.py)::(\w+)::(\w+)\s+(PASSED|FAILED|ERROR)/);
        if (testMatch) {
            const [, file, className, testName, status] = testMatch;
            const testKey = `${file}::${className}::${testName}`;
            
            if (!testMap.has(testKey)) {
                testMap.set(testKey, {
                    file: file.replace('.py', ''),
                    class: className,
                    test: testName,
                    status: status.toLowerCase(),
                    details: ''
                });
            }
            
            const test = testMap.get(testKey);
            if (status === 'PASSED') {
                results.passedCount++;
                results.total++;
                test.status = 'passed';
                results.passed.push(test);
            } else {
                results.failedCount++;
                results.total++;
                test.status = status.toLowerCase();
                results.failed.push(test);
            }
        }

        const failureMatch = line.match(/FAILED\s+(test_\w+\.py)::(\w+)::(\w+)\s+-\s+(.+)/);
        if (failureMatch) {
            const [, file, className, testName, errorMsg] = failureMatch;
            const testKey = `${file}::${className}::${testName}`;
            if (testMap.has(testKey)) {
                testMap.get(testKey).details = errorMsg;
            }
        }

        const assertionMatch = line.match(/AssertionError:\s*(.+)/);
        if (assertionMatch) {
            for (const [key, test] of testMap.entries()) {
                if (test.status !== 'passed' && !test.details) {
                    test.details = assertionMatch[1];
                    break;
                }
            }
        }

        const durationMatch = line.match(/(\d+\.\d+)s/);
        if (durationMatch) {
            results.duration = parseFloat(durationMatch[1]);
        }
    }

    return results;
}

function displayResults(results) {
    console.log('\n' + '='.repeat(80));
    console.log(colorize('RÉSULTATS DES TESTS', colors.bright + colors.cyan));
    console.log('='.repeat(80) + '\n');

    if (results.passed.length > 0 && results.passed.length <= 20) {
        console.log(colorize(`✓ Tests réussis: ${results.passedCount}`, colors.green));
        results.passed.forEach(test => {
            console.log(`  ${colorize('✓', colors.green)} ${test.file}::${test.class}::${test.test}`);
        });
        console.log('');
    } else if (results.passed.length > 20) {
        console.log(colorize(`✓ Tests réussis: ${results.passedCount}`, colors.green));
        console.log(colorize(`  (Liste complète masquée pour ${results.passedCount} tests)`, colors.gray));
        console.log('');
    }

    if (results.failed.length > 0) {
        console.log(colorize(`✗ Tests échoués: ${results.failedCount}`, colors.red + colors.bright));
        results.failed.forEach((test, index) => {
            console.log(`\n  ${colorize(`${index + 1}.`, colors.yellow)} ${colorize('✗', colors.red)} ${test.file}::${test.class}::${test.test}`);
            if (test.details && test.details.trim()) {
                const details = test.details.split('\n').filter(l => l.trim()).slice(0, 3);
                if (details.length > 0) {
                    console.log(colorize(`     ${details.join('\n     ')}`, colors.gray));
                }
            }
        });
        console.log('');
    }

    console.log('─'.repeat(80));
    const total = results.passedCount + results.failedCount;
    const successRate = total > 0 ? ((results.passedCount / total) * 100).toFixed(1) : 0;
    
    if (results.failedCount === 0) {
        console.log(colorize(`\n✓ Tous les tests sont passés! (${results.passedCount}/${total})`, colors.green + colors.bright));
    } else {
        console.log(colorize(`\n✗ ${results.failedCount} test(s) ont échoué sur ${total}`, colors.red + colors.bright));
    }
    
    console.log(colorize(`Taux de réussite: ${successRate}%`, colors.cyan));
    if (results.duration) {
        console.log(colorize(`Durée totale: ${results.duration.toFixed(2)}s`, colors.gray));
    }
    console.log('='.repeat(80) + '\n');
}

async function runTests(testFile = null) {
    console.log(colorize('Exécution des tests...', colors.blue + colors.bright));
    console.log('─'.repeat(80) + '\n');

    try {
        const command = testFile 
            ? `python3 -m pytest tests/${testFile} -v --tb=line`
            : `python3 -m pytest tests/ -v --tb=line`;
        
        const { stdout, stderr } = await execAsync(command, {
            cwd: process.cwd(),
            maxBuffer: 1024 * 1024 * 10
        });

        const results = parsePytestOutput(stdout);
        displayResults(results);

        if (stderr && !stderr.includes('WARNING')) {
            console.log(colorize('Avertissements:', colors.yellow));
            console.log(stderr);
        }

        if (results.failedCount > 0) {
            process.exit(1);
        } else {
            process.exit(0);
        }
    } catch (error) {
        if (error.stdout) {
            const results = parsePytestOutput(error.stdout);
            if (results.total > 0) {
                displayResults(results);
                process.exit(results.failedCount > 0 ? 1 : 0);
                return;
            }
        }
        
        console.error(colorize('\n✗ Erreur lors de l\'exécution des tests:', colors.red + colors.bright));
        console.error(error.message);
        
        if (error.stdout) {
            console.log('\n' + colorize('Sortie standard:', colors.yellow));
            console.log(error.stdout);
        }
        
        if (error.stderr && !error.stderr.includes('WARNING')) {
            console.log('\n' + colorize('Erreurs:', colors.red));
            console.log(error.stderr);
        }
        
        process.exit(1);
    }
}

const args = process.argv.slice(2);
const testFile = args[0] || null;

if (testFile && !testFile.endsWith('.py')) {
    console.error(colorize('Erreur: Le fichier de test doit se terminer par .py', colors.red));
    process.exit(1);
}

runTests(testFile);

