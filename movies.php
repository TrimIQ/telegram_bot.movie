<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');
header('Access-Control-Allow-Headers: Content-Type');

// File path for JSON storage
$jsonFile = 'movies.json';

// Ensure file exists
if (!file_exists($jsonFile)) {
    file_put_contents($jsonFile, json_encode([]));
}

function loadMovies() {
    global $jsonFile;
    $content = file_get_contents($jsonFile);
    return json_decode($content, true) ?: [];
}

function saveMovies($movies) {
    global $jsonFile;
    file_put_contents($jsonFile, json_encode($movies, JSON_PRETTY_PRINT));
}

$input = json_decode(file_get_contents('php://input'), true);
$action = $input['action'] ?? '';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['status' => 'error', 'message' => 'Method not allowed']);
    exit;
}

switch ($action) {
    case 'search':
        $movie = strtolower(trim($input['movie'] ?? ''));
        
        if (empty($movie)) {
            echo json_encode(['status' => 'not_found']);
            exit;
        }
        
        $movies = loadMovies();
        $foundKey = '';
        
        // Case-insensitive exact match
        foreach ($movies as $key => $link) {
            if (strtolower($key) === $movie) {
                $foundKey = $key;
                break;
            }
        }
        
        if ($foundKey) {
            echo json_encode([
                'status' => 'found',
                'link' => $movies[$foundKey]
            ]);
        } else {
            echo json_encode(['status' => 'not_found']);
        }
        break;
        
    case 'add':
        $movie = strtolower(trim($input['movie'] ?? ''));
        $link = trim($input['link'] ?? '');
        
        if (empty($movie) || empty($link)) {
            echo json_encode(['status' => 'error', 'message' => 'Movie name and link required']);
            exit;
        }
        
        $movies = loadMovies();
        $movies[$movie] = $link;
        saveMovies($movies);
        
        echo json_encode([
            'status' => 'success',
            'message' => 'Movie added successfully'
        ]);
        break;
        
    default:
        echo json_encode(['status' => 'error', 'message' => 'Invalid action']);
}
?>