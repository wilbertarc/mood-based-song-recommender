"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Music,
  Sparkles,
  Heart,
  Play,
  Star,
  Headphones,
  Volume2,
} from "lucide-react";

interface Song {
  title: string;
  artist: string;
  matchScore: number;
  genre?: string;
  mood?: string;
}

export default function MoodSongRecommender() {
  const [moodDescription, setMoodDescription] = useState("");
  const [songCount, setSongCount] = useState([5]);
  const [recommendations, setRecommendations] = useState<Song[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleRecommend = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("http://localhost:5000/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          diary_text: moodDescription,
          rec_n: songCount[0], // send number of songs to backend
        }),
      });

      const data = await res.json();

      // data is an array of {spotify_id, name, artist, score}
      const formatted: Song[] = data.map((song: any) => ({
        title: song.name, // backend returns 'name'
        artist: song.artist,
        matchScore: Math.round(song.score * 100), // scale 0-1 to 0-100
        // Optionally add a Spotify link:
        // link: song.spotify_id ? `https://open.spotify.com/track/${song.spotify_id}` : undefined,
      }));

      setRecommendations(formatted); // already limited by backend
    } catch (err) {
      console.error("Failed to fetch recommendations", err);
    }
    setIsLoading(false);
  };

  const getMoodColor = (score: number) => {
    if (score >= 0.9) return "bg-green-500";
    if (score >= 0.8) return "bg-blue-500";
    if (score >= 0.7) return "bg-yellow-500";
    return "bg-gray-500";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8 pt-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-pink-500 to-violet-500 rounded-full">
              <Music className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-pink-400 to-violet-400 bg-clip-text text-transparent">
              Mood-Based Song Recommender
            </h1>
          </div>
          <div className="flex items-center justify-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-yellow-400" />
            <p className="text-lg text-gray-300">
              Powered by AI + Spotify + Lyrics Embeddings
            </p>
            <Sparkles className="w-5 h-5 text-yellow-400" />
          </div>
          <p className="text-xl text-gray-200 max-w-2xl mx-auto">
            Just describe how your day went, and this AI will find songs that
            match your mood.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <Card className="bg-white/10 backdrop-blur-lg border-white/20 shadow-2xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Heart className="w-5 h-5 text-pink-400" />
                Tell us about your mood
              </CardTitle>
              <CardDescription className="text-gray-300">
                Share your feelings, experiences, or what kind of vibe you're
                looking for
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Textarea
                  placeholder="e.g., I feel happy and energetic after hanging out with friends! Looking for something upbeat to keep the good vibes going..."
                  value={moodDescription}
                  onChange={(e) => setMoodDescription(e.target.value)}
                  className="min-h-[120px] bg-white/5 border-white/20 text-white placeholder:text-gray-400 focus:border-pink-400 focus:ring-pink-400"
                />
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-white font-medium flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-blue-400" />
                    Number of Songs
                  </label>
                  <Badge variant="secondary" className="bg-white/20 text-white">
                    {songCount[0]} songs
                  </Badge>
                </div>
                <Slider
                  value={songCount}
                  onValueChange={setSongCount}
                  max={15}
                  min={1}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-gray-400">
                  <span>1</span>
                  <span>15</span>
                </div>
              </div>

              <Button
                onClick={handleRecommend}
                disabled={!moodDescription.trim() || isLoading}
                className="w-full bg-gradient-to-r from-pink-500 to-violet-500 hover:from-pink-600 hover:to-violet-600 text-white font-semibold py-3 text-lg shadow-lg hover:shadow-xl transition-all duration-200"
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Finding your perfect songs...
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Headphones className="w-5 h-5" />
                    Recommend Songs
                  </div>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Section */}
          <Card className="bg-white/10 backdrop-blur-lg border-white/20 shadow-2xl">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-400" />
                Your Personalized Playlist
              </CardTitle>
              <CardDescription className="text-gray-300">
                Songs that match your current mood and energy
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recommendations.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-gradient-to-r from-pink-500/20 to-violet-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Music className="w-10 h-10 text-gray-400" />
                  </div>
                  <p className="text-gray-400 text-lg">
                    Your song recommendations will appear here
                  </p>
                  <p className="text-gray-500 text-sm mt-2">
                    Describe your mood above to get started
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recommendations.map((song, index) => (
                    <div
                      key={index}
                      className="group bg-white/5 hover:bg-white/10 rounded-lg p-4 transition-all duration-200 hover:shadow-lg border border-white/10 hover:border-white/20"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <div className="w-12 h-12 bg-gradient-to-r from-pink-500 to-violet-500 rounded-lg flex items-center justify-center">
                            <Play className="w-6 h-6 text-white" />
                          </div>
                          <div className="flex-1">
                            <h3 className="text-white font-semibold text-lg group-hover:text-pink-300 transition-colors">
                              {song.title}
                            </h3>
                            <p className="text-gray-300 text-sm">
                              {song.artist}
                            </p>
                            <div className="flex gap-2 mt-1">
                              {song.genre && (
                                <Badge
                                  variant="outline"
                                  className="text-xs border-blue-400/50 text-blue-300"
                                >
                                  {song.genre}
                                </Badge>
                              )}
                              {song.mood && (
                                <Badge
                                  variant="outline"
                                  className="text-xs border-pink-400/50 text-pink-300"
                                >
                                  {song.mood}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-2">
                            <div
                              className={`w-3 h-3 rounded-full ${getMoodColor(
                                song.matchScore
                              )}`}
                            />
                            <span className="text-white font-bold text-lg">
                              {song.matchScore}%
                            </span>
                          </div>
                          <p className="text-gray-400 text-xs">match</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <div className="text-center mt-12 pb-8">
          <p className="text-gray-400 text-sm">
            Discover music that resonates with your soul ✨
          </p>
        </div>
      </div>
    </div>
  );
}
