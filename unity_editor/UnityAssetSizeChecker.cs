using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace ArdanR3.Pipeline
{
    /// <summary>
    /// Scans Assets/ for large files that may trigger GitHub's 50 MB warning or 100 MB limit.
    /// </summary>
    public class UnityAssetSizeChecker : EditorWindow
    {
        private float _thresholdMb = 25f;
        private Vector2 _scroll;
        private readonly List<(string path, float mb)> _results = new List<(string, float)>();

        [MenuItem("Tools/Pipeline/Check Large Assets")]
        public static void ShowWindow()
        {
            GetWindow<UnityAssetSizeChecker>("Asset Size Checker");
        }

        private void OnGUI()
        {
            GUILayout.Label("GitHub Large Asset Checker", EditorStyles.boldLabel);
            _thresholdMb = EditorGUILayout.Slider("Threshold (MB)", _thresholdMb, 5f, 100f);

            if (GUILayout.Button("Scan Assets Folder"))
            {
                ScanAssets();
            }

            GUILayout.Space(8);
            _scroll = EditorGUILayout.BeginScrollView(_scroll);
            foreach (var item in _results)
            {
                string tag = item.mb >= 100f ? "[BLOCKED >100MB]" : (item.mb >= 50f ? "[WARN >50MB]" : "[HEAVY]");
                EditorGUILayout.BeginHorizontal();
                EditorGUILayout.LabelField($"{tag} {item.mb:F2} MB", GUILayout.Width(170));
                if (GUILayout.Button(item.path, EditorStyles.linkLabel))
                {
                    var obj = AssetDatabase.LoadMainAssetAtPath(item.path);
                    if (obj != null) Selection.activeObject = obj;
                }
                EditorGUILayout.EndHorizontal();
            }
            EditorGUILayout.EndScrollView();
        }

        private void ScanAssets()
        {
            _results.Clear();
            string assetsRoot = Application.dataPath;
            foreach (string file in Directory.GetFiles(assetsRoot, "*", SearchOption.AllDirectories))
            {
                if (file.EndsWith(".meta")) continue;
                var info = new FileInfo(file);
                float mb = info.Length / (1024f * 1024f);
                if (mb >= _thresholdMb)
                {
                    string rel = "Assets" + file.Substring(assetsRoot.Length).Replace('\\', '/');
                    _results.Add((rel, mb));
                }
            }
            _results.Sort((a, b) => b.mb.CompareTo(a.mb));
        }
    }
}
